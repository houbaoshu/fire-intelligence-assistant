"""切分测试：条文号优先切分、回退段落切分、chunk 元数据完整性。"""

from app.rag.chunking import DocumentMeta, chunk_document
from app.rag.parsers.base import ParsedBlock

META = DocumentMeta(
    document_id="doc-1",
    title="中华人民共和国消防法",
    document_type="regulation",
    source_path="knowledge/x.pdf",
    version="2021 修正",
    effective_date="2021-04-29",
    issuing_authority="全国人民代表大会常务委员会",
)

REQUIRED_METADATA_KEYS = {
    "document_id",
    "title",
    "document_type",
    "page",
    "article_number",
    "section",
    "source_path",
    "version",
    "effective_date",
    "issuing_authority",
}


def test_article_splitting():
    text = (
        "中华人民共和国消防法\n"
        "第一章 总则\n"
        "第一条 为了预防火灾和减少火灾危害，制定本法。\n"
        "第二条 消防工作贯彻预防为主、防消结合的方针。\n"
        "第二章 火灾预防\n"
        "第二十八条 任何单位、个人不得损坏、挪用消防设施，不得锁闭安全出口。"
    )
    chunks = chunk_document([ParsedBlock(text=text, page=12)], META)
    articles = [c.metadata["article_number"] for c in chunks]
    assert articles.count("第一条") == 1
    assert articles.count("第二条") == 1
    assert articles.count("第二十八条") == 1
    # 文首序言（标题）独立成 chunk，条文号为空
    assert any(c.metadata["article_number"] is None for c in chunks)
    article_28 = next(c for c in chunks if c.metadata["article_number"] == "第二十八条")
    assert "安全出口" in article_28.content
    assert article_28.metadata["page"] == 12
    assert article_28.metadata["section"] == "第二章 火灾预防"
    first = next(c for c in chunks if c.metadata["article_number"] == "第一条")
    assert first.metadata["section"] == "第一章 总则"


def test_metadata_completeness():
    chunks = chunk_document([ParsedBlock(text="第一条 内容。")], META)
    assert chunks
    for chunk in chunks:
        assert set(chunk.metadata) == REQUIRED_METADATA_KEYS
        assert chunk.metadata["document_id"] == "doc-1"
        assert chunk.metadata["effective_date"] == "2021-04-29"
        assert chunk.metadata["issuing_authority"] == "全国人民代表大会常务委员会"


def test_fallback_paragraph_splitting_when_no_articles():
    text = "\n\n".join(f"第{i}段说明文字。" * 30 for i in range(5))
    chunks = chunk_document([ParsedBlock(text=text)], META)
    assert len(chunks) > 1
    assert all(c.metadata["article_number"] is None for c in chunks)
    assert all(len(c.content) <= 600 for c in chunks)


def test_long_article_split_keeps_article_number():
    long_article = "第五十条 " + "很长" * 600
    chunks = chunk_document([ParsedBlock(text=long_article)], META)
    assert len(chunks) > 1
    assert all(c.metadata["article_number"] == "第五十条" for c in chunks)
    assert all(len(c.content) <= 800 for c in chunks)


def test_chunk_index_stable_and_ordered():
    text = "第一条 甲。\n第二条 乙。\n第三条 丙。"
    chunks = chunk_document([ParsedBlock(text=text)], META)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
