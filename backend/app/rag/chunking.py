from __future__ import annotations

from typing import Any


def chunk_sections(
    sections: list[tuple[str, dict[str, Any]]], *, size: int, overlap: int
) -> list[tuple[str, dict[str, Any]]]:
    chunks: list[tuple[str, dict[str, Any]]] = []
    for text, metadata in sections:
        normalized = "\n".join(line.strip() for line in text.splitlines() if line.strip())
        start = 0
        while start < len(normalized):
            end = min(len(normalized), start + size)
            if end < len(normalized):
                boundary = max(
                    normalized.rfind("\n", start, end), normalized.rfind("。", start, end)
                )
                if boundary > start + size // 2:
                    end = boundary + 1
            content = normalized[start:end].strip()
            if content:
                chunks.append((content, dict(metadata)))
            if end >= len(normalized):
                break
            start = max(start + 1, end - overlap)
    return chunks
