"""语义切分（ARCHITECTURE.md §10.1）。

策略：优先按法规条文号（第X条）切分 —— 每个条文一个 chunk，条文前的
标题/序言部分独立成 chunk；全文无条文号时回退为按段落 + 长度切分。
超长条文按行/长度二次切分（chunk 仍携带该条文号）。

chunk 元数据字段（specs/knowledge-base.md「字段清单」，全仓库唯一定义）：
document_id、title、document_type、version、page、section（章/节）、
article_number、source_path、effective_date、issuing_authority。
"""

import re
from dataclasses import dataclass

from app.rag.parsers.base import ParsedBlock

_CN_NUM = "0-9０-９一二三四五六七八九十百千零〇两"
ARTICLE_RE = re.compile(rf"第[{_CN_NUM}]+条")
_CHAPTER_RE = re.compile(rf"第[{_CN_NUM}]+章[^\n。]*")
_SECTION_RE = re.compile(rf"第[{_CN_NUM}]+节[^\n。]*")

# 条文模式下单个 chunk 的最大长度（超长条文二次切分）
MAX_CHUNK_CHARS = 800
# 回退模式（无条文号）下的目标 chunk 长度
FALLBACK_CHUNK_CHARS = 500


@dataclass
class DocumentMeta:
    """文档级元数据（来自 knowledge_documents，切分时增强到每个 chunk）。"""

    document_id: str
    title: str
    document_type: str | None = None
    source_path: str | None = None
    version: str | None = None
    effective_date: str | None = None  # ISO 日期字符串
    issuing_authority: str | None = None


@dataclass
class Chunk:
    content: str
    chunk_index: int
    metadata: dict


@dataclass
class _Segment:
    text: str
    page: int | None
    article_number: str | None
    section: str | None


def _join_section(chapter: str | None, section: str | None) -> str | None:
    parts = [p for p in (chapter, section) if p]
    return " ".join(parts) if parts else None


def _split_articles(blocks: list[ParsedBlock]) -> list[_Segment]:
    """按条文号切分；条文间文本归入前一个条文，文首序言为 article=None 段。"""
    segments: list[_Segment] = []
    buffer: list[str] = []
    buffer_page: int | None = None
    chapter: str | None = None
    section: str | None = None

    def update_headers(text: str) -> None:
        nonlocal chapter, section
        for m in _CHAPTER_RE.finditer(text):
            chapter = m.group().strip()
            section = None
        for m in _SECTION_RE.finditer(text):
            section = m.group().strip()

    def flush() -> None:
        nonlocal buffer, buffer_page
        text = "\n".join(buffer).strip()
        if text:
            segments.append(
                _Segment(
                    text=text,
                    page=buffer_page,
                    article_number=None,
                    section=_join_section(chapter, section),
                )
            )
        buffer = []
        buffer_page = None

    for block in blocks:
        text = block.text
        matches = list(ARTICLE_RE.finditer(text))
        if not matches:
            update_headers(text)
            if buffer_page is None:
                buffer_page = block.page
            buffer.append(text)
            continue
        pre = text[: matches[0].start()]
        update_headers(pre)
        if pre.strip():
            if buffer_page is None:
                buffer_page = block.page
            buffer.append(pre)
        flush()
        for i, m in enumerate(matches):
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            seg_section = _join_section(chapter, section)
            seg_text = text[m.start() : end]
            update_headers(seg_text)  # 段内章/节标题作用于后续条文
            segments.append(
                _Segment(
                    text=seg_text.strip(),
                    page=block.page,
                    article_number=m.group(),
                    section=seg_section,
                )
            )
    flush()
    return segments


def _hard_split(text: str, max_chars: int) -> list[str]:
    return [text[i : i + max_chars] for i in range(0, len(text), max_chars)]


def _split_long(segment: _Segment, max_chars: int) -> list[_Segment]:
    """超长段按行归并、必要时硬切分；子段继承页码/条文号/章节。"""
    if len(segment.text) <= max_chars:
        return [segment]
    pieces: list[str] = []
    buf = ""
    for line in segment.text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if len(line) > max_chars:
            if buf:
                pieces.append(buf)
                buf = ""
            pieces.extend(_hard_split(line, max_chars))
        elif buf and len(buf) + len(line) + 1 > max_chars:
            pieces.append(buf)
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        pieces.append(buf)
    return [
        _Segment(
            text=piece,
            page=segment.page,
            article_number=segment.article_number,
            section=segment.section,
        )
        for piece in pieces
    ]


def _pack_paragraphs(blocks: list[ParsedBlock], max_chars: int) -> list[_Segment]:
    """回退策略：按段落归并为不超过 max_chars 的 chunk。"""
    pieces: list[_Segment] = []
    buf = ""
    buf_page: int | None = None

    def flush() -> None:
        nonlocal buf, buf_page
        if buf.strip():
            pieces.append(
                _Segment(text=buf.strip(), page=buf_page, article_number=None, section=None)
            )
        buf = ""
        buf_page = None

    for block in blocks:
        for para in re.split(r"\n+", block.text):
            para = para.strip()
            if not para:
                continue
            if len(para) > max_chars:
                flush()
                for part in _hard_split(para, max_chars):
                    pieces.append(
                        _Segment(
                            text=part,
                            page=block.page,
                            article_number=None,
                            section=None,
                        )
                    )
            elif buf and len(buf) + len(para) + 1 > max_chars:
                flush()
                buf = para
                buf_page = block.page
            else:
                if buf_page is None:
                    buf_page = block.page
                buf = f"{buf}\n{para}" if buf else para
    flush()
    return pieces


def _build_metadata(meta: DocumentMeta, segment: _Segment) -> dict:
    return {
        "document_id": meta.document_id,
        "title": meta.title,
        "document_type": meta.document_type,
        "page": segment.page,
        "article_number": segment.article_number,
        "section": segment.section,
        "source_path": meta.source_path,
        "version": meta.version,
        "effective_date": meta.effective_date,
        "issuing_authority": meta.issuing_authority,
    }


def chunk_document(
    blocks: list[ParsedBlock], meta: DocumentMeta, *, max_chars: int = MAX_CHUNK_CHARS
) -> list[Chunk]:
    """切分文档为带元数据的 chunk 列表（chunk_index 从 0 开始，稳定有序）。"""
    segments = _split_articles(blocks)
    if any(s.article_number for s in segments):
        pieces = [p for seg in segments for p in _split_long(seg, max_chars)]
    else:
        pieces = _pack_paragraphs(blocks, FALLBACK_CHUNK_CHARS)
    return [
        Chunk(content=piece.text, chunk_index=i, metadata=_build_metadata(meta, piece))
        for i, piece in enumerate(pieces)
        if piece.text
    ]
