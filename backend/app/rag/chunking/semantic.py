"""Semantic chunking for splitting documents into overlapping segments.

Splits text by paragraphs first, then by sentences for paragraphs that
exceed the target chunk size.  Adjacent chunks share an overlap region
to preserve context across boundaries.
"""

from __future__ import annotations

import re

from app.core.logging import get_logger

logger = get_logger(__name__)

# Sentence-ending punctuation patterns (supports CJK and Latin)
_SENTENCE_END_RE = re.compile(r"(?<=[.!?。！？\n])\s*")


class SemanticChunker:
    """Split documents into semantic chunks for embedding.

    Parameters
    ----------
    chunk_size:
        Target maximum number of characters per chunk.
    chunk_overlap:
        Number of overlapping characters between consecutive chunks.
    """

    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50) -> None:
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict | None = None) -> list[dict]:
        """Split text into overlapping chunks with metadata.

        The algorithm works in three stages:

        1. Split by paragraphs (double newlines).
        2. If a paragraph exceeds *chunk_size*, split it further by
           sentences.
        3. Merge small segments into chunks that respect *chunk_size*
           while maintaining *chunk_overlap* characters of overlap
           between consecutive chunks.

        Args:
            text: The full document text.
            metadata: Optional source metadata to include in every chunk.

        Returns:
            List of dicts with ``text`` and ``metadata`` keys.
            Metadata includes ``chunk_index``, ``total_chunks``, and
            any source metadata provided.
        """
        if not text or not text.strip():
            return []

        base_metadata = metadata or {}

        # Stage 1: split into paragraphs
        paragraphs = self._split_by_paragraphs(text)

        # Stage 2: further split large paragraphs by sentences
        segments: list[str] = []
        for para in paragraphs:
            if len(para) <= self.chunk_size:
                segments.append(para)
            else:
                sentences = self._split_by_sentences(para)
                segments.extend(sentences)

        # Stage 3: merge segments into sized chunks with overlap
        chunks = self._merge_chunks(segments, base_metadata)

        # Annotate chunk_index and total_chunks
        total = len(chunks)
        for idx, chunk in enumerate(chunks):
            chunk["metadata"]["chunk_index"] = idx
            chunk["metadata"]["total_chunks"] = total

        logger.info(
            "Chunked text",
            extra={
                "text_length": len(text),
                "num_chunks": total,
                "chunk_size": self.chunk_size,
            },
        )

        return chunks

    def _split_by_paragraphs(self, text: str) -> list[str]:
        """Split text by paragraph breaks (one or more blank lines)."""
        # Split on double newlines (with optional whitespace)
        raw_parts = re.split(r"\n\s*\n", text.strip())
        return [p.strip() for p in raw_parts if p.strip()]

    def _split_by_sentences(self, text: str) -> list[str]:
        """Split text into individual sentences.

        Handles both Latin (``.!?``) and CJK (``。！？``) sentence
        terminators.
        """
        # Split on sentence-ending punctuation
        parts = _SENTENCE_END_RE.split(text.strip())
        return [s.strip() for s in parts if s.strip()]

    def _merge_chunks(self, segments: list[str], metadata: dict) -> list[dict]:
        """Merge small segments into chunks respecting size limits.

        Consecutive chunks overlap by up to *chunk_overlap* characters
        taken from the tail of the previous chunk.
        """
        if not segments:
            return []

        chunks: list[dict] = []
        current_parts: list[str] = []
        current_length = 0

        for segment in segments:
            segment_len = len(segment)

            # If adding this segment would exceed chunk_size and we
            # already have content, flush the current chunk.
            if current_parts and (current_length + segment_len + 1) > self.chunk_size:
                chunk_text = "\n".join(current_parts)
                chunks.append(
                    {
                        "text": chunk_text,
                        "metadata": {**metadata},
                    }
                )

                # Compute overlap: carry trailing characters into the
                # next chunk so context is preserved.
                overlap_text = chunk_text[-self.chunk_overlap :] if self.chunk_overlap else ""
                if overlap_text:
                    current_parts = [overlap_text, segment]
                    current_length = len(overlap_text) + segment_len + 1
                else:
                    current_parts = [segment]
                    current_length = segment_len
            else:
                current_parts.append(segment)
                current_length += segment_len + 1  # +1 for newline

        # Flush remaining content
        if current_parts:
            chunk_text = "\n".join(current_parts)
            chunks.append(
                {
                    "text": chunk_text,
                    "metadata": {**metadata},
                }
            )

        return chunks
