"""PDF 解析（pypdf）：每页一个文本块，保留 1-based 页码。"""

import io

from app.rag.parsers.base import ParsedBlock, ParsedDocument, parse_error


def parse_pdf(data: bytes) -> ParsedDocument:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise parse_error("PDF 解析组件未安装，请联系管理员")
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise parse_error("PDF 文件已加密，无法解析，请提供未加密版本")
        blocks = []
        for i, page in enumerate(reader.pages, start=1):
            text = (page.extract_text() or "").strip()
            if text:
                blocks.append(ParsedBlock(text=text, page=i))
    except Exception as exc:
        from app.core.exceptions import AppException

        if isinstance(exc, AppException):
            raise
        raise parse_error("PDF 文件损坏或格式不受支持，无法解析")
    return ParsedDocument(blocks=blocks)
