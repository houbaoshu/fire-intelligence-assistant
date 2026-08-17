"""文档解析器共享类型。

解析输出为保留页码信息（可获得时）的文本块列表；解析失败抛可读
``AppException``（``DOCUMENT_PARSE_ERROR`` / ``DOCUMENT_PARSE_UNSUPPORTED``），
错误信息不携带内部堆栈（specs/knowledge-base.md 安全规则）。
"""

from dataclasses import dataclass, field

from app.core.exceptions import AppException


@dataclass
class ParsedBlock:
    text: str
    page: int | None = None  # 1-based 页码（PDF 页 / PPTX 幻灯片）；无法获得时为 None


@dataclass
class ParsedDocument:
    blocks: list[ParsedBlock] = field(default_factory=list)


def parse_error(message: str) -> AppException:
    return AppException("DOCUMENT_PARSE_ERROR", message, 400)


def parse_unsupported(message: str) -> AppException:
    return AppException("DOCUMENT_PARSE_UNSUPPORTED", message, 400)
