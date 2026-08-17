"""按扩展名分发解析（API.md §9 文档类别）。

旧版二进制格式（.doc / .ppt）无轻量解析依赖，明确报可读错误而不是
静默失败或产出乱码；用户可转换为 .docx / .pptx 后重新上传。
"""

from app.rag.parsers.base import (
    ParsedBlock,
    ParsedDocument,
    parse_unsupported,
)
from app.rag.parsers.docx import parse_docx
from app.rag.parsers.pdf import parse_pdf
from app.rag.parsers.pptx import parse_pptx
from app.rag.parsers.text import parse_text

_PARSERS = {
    ".txt": parse_text,
    ".md": parse_text,
    ".pdf": parse_pdf,
    ".docx": parse_docx,
    ".pptx": parse_pptx,
}

SUPPORTED_EXTENSIONS = tuple(sorted(_PARSERS))


def parse_document(extension: str, data: bytes) -> ParsedDocument:
    """按扩展名解析文档为文本块；失败抛可读 AppException。"""
    ext = extension.lower()
    if ext in (".doc", ".ppt"):
        raise parse_unsupported(
            f"旧版二进制格式 {ext} 暂不支持解析，请转换为 "
            f"{'.docx' if ext == '.doc' else '.pptx'} 后重新上传"
        )
    parser = _PARSERS.get(ext)
    if parser is None:
        raise parse_unsupported(f"不支持解析的文档格式: {ext or '(无扩展名)'}")
    return parser(data)


__all__ = [
    "SUPPORTED_EXTENSIONS",
    "ParsedBlock",
    "ParsedDocument",
    "parse_document",
]
