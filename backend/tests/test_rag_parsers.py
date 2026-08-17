"""解析器测试：txt/md/docx/pptx/pdf 解析与不支持的旧格式可读错误。"""

import pytest

from app.core.exceptions import AppException
from app.rag.parsers import parse_document
from tests.helpers import make_docx, make_minimal_pdf, make_pptx


def test_parse_txt_utf8():
    result = parse_document(".txt", "第一条 内容。\n\n第二条 内容。".encode("utf-8"))
    assert len(result.blocks) == 2
    assert result.blocks[0].page is None


def test_parse_txt_gb18030():
    result = parse_document(".txt", "消防法规正文".encode("gb18030"))
    assert result.blocks[0].text == "消防法规正文"


def test_parse_txt_invalid_encoding():
    with pytest.raises(AppException) as exc_info:
        parse_document(".txt", b"\xff\xfe\x00\x01invalid\x99\x98")
    assert exc_info.value.code == "DOCUMENT_PARSE_ERROR"


def test_parse_md():
    result = parse_document(".md", "# 标题\n\n正文段落".encode("utf-8"))
    assert len(result.blocks) == 2


def test_parse_docx():
    data = make_docx(["第一章 总则", "第一条 为了加强消防工作。"])
    result = parse_document(".docx", data)
    texts = [b.text for b in result.blocks]
    assert texts == ["第一章 总则", "第一条 为了加强消防工作。"]


def test_parse_pptx_keeps_slide_pages():
    result = parse_document(".pptx", make_pptx(["第一页", "第二页"]))
    assert [b.text for b in result.blocks] == ["第一页", "第二页"]
    assert [b.page for b in result.blocks] == [1, 2]


def test_parse_pdf_keeps_page_numbers():
    result = parse_document(".pdf", make_minimal_pdf("Fire safety rules"))
    assert len(result.blocks) == 1
    assert result.blocks[0].page == 1
    assert "Fire safety rules" in result.blocks[0].text


def test_parse_pdf_corrupted():
    with pytest.raises(AppException) as exc_info:
        parse_document(".pdf", b"%PDF-1.4 broken garbage")
    assert exc_info.value.code == "DOCUMENT_PARSE_ERROR"


def test_parse_doc_ppt_unsupported_readable():
    for ext, target in ((".doc", ".docx"), (".ppt", ".pptx")):
        with pytest.raises(AppException) as exc_info:
            parse_document(ext, b"ole2-bytes")
        assert exc_info.value.code == "DOCUMENT_PARSE_UNSUPPORTED"
        assert target in exc_info.value.message
