"""Semantic chunking for regulations.

Strategy: split on article/section headings first (preserves article numbers),
then merge/split by character budget with overlap. Article numbers are
captured into chunk metadata (specs/knowledge-base.md chunk metadata list).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

ARTICLE_RE = re.compile(r"^(第[一二三四五六七八九十百千万零〇]+条)\s*(.*)$")


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)
    chunk_id: str | None = None
    embedding: list[float] | None = None


def _split_headings(text: str) -> list[tuple[str | None, str]]:
    """Return list of (article_number, block_text)."""
    lines = text.split("\n")
    blocks: list[tuple[str | None, list[str]]] = []
    current_article: str | None = None
    current: list[str] = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        m = ARTICLE_RE.match(line)
        if m:
            if current:
                blocks.append((current_article, current))
            current_article = m.group(1)
            current = [line]
        else:
            current.append(line)
    if current:
        blocks.append((current_article, current))
    return [(a, "\n".join(lines)) for a, lines in blocks]


def chunk_document(
    text: str,
    *,
    doc_metadata: dict,
    max_chars: int = 800,
    overlap_chars: int = 100,
) -> list[Chunk]:
    """Chunk normalized document text, preserving article metadata."""
    raw_blocks = _split_headings(text)
    chunks: list[Chunk] = []
    for article, block in raw_blocks:
        # further split long blocks on blank-line paragraph boundaries
        paragraphs = re.split(r"\n{2,}", block)
        buffer = ""
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(buffer) + len(para) + 1 <= max_chars:
                buffer = f"{buffer}\n{para}" if buffer else para
            else:
                if buffer:
                    chunks.append((article, buffer))
                # very long paragraph: hard-split with overlap
                if len(para) > max_chars:
                    start = 0
                    while start < len(para):
                        end = min(start + max_chars, len(para))
                        pieces = para[start:end]
                        chunks.append((article, pieces))
                        if end >= len(para):
                            break
                        start = end - overlap_chars
                else:
                    buffer = para
        if buffer:
            chunks.append((article, buffer))

    result: list[Chunk] = []
    for article, ctext in chunks:
        meta = dict(doc_metadata)
        if article:
            meta["article"] = article
        result.append(Chunk(text=ctext.strip(), metadata=meta))
    return [c for c in result if c.text]
