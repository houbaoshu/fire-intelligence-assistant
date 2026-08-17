"""RAG 子系统（ARCHITECTURE.md §10）。

索引管线：源文档 → 解析（parsers）→ 规范化 → 语义切分（chunking）→
元数据增强 → Embedding（services/ai/embedding）→ 向量库（embedding/store）。
查询管线：问题 → Retriever（retrieval）→ Reranker（reranking）→
上下文构建 → LLM → 答案+引用（query.py）。

向量库只存检索数据与 chunk 元数据，业务事实源始终在关系数据库。
"""
