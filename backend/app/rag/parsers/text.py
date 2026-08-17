"""纯文本 / Markdown 解析：按空行分段，页码不可得（None）。"""

from app.rag.parsers.base import ParsedBlock, ParsedDocument, parse_error


def parse_text(data: bytes) -> ParsedDocument:
    text: str | None = None
    for encoding in ("utf-8", "gb18030"):
        try:
            text = data.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise parse_error("文本文件编码无法识别（支持 UTF-8 / GB18030）")
    blocks = [
        ParsedBlock(text=chunk.strip())
        for chunk in text.split("\n\n")
        if chunk.strip()
    ]
    return ParsedDocument(blocks=blocks)
