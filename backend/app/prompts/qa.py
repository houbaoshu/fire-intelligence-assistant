"""法规问答 Prompt（API.md §5 / specs/regulation-qa.md）。

约束来源：
- RAG 启用时禁止 LLM 凭想象作答（AGENTS.md RAG 规则）；
- 答案必须区分检索事实与模型解读（ARCHITECTURE.md §10.2）；
- 禁止编造法律名称、条款编号、发文机关、生效日期或引文（specs/regulation-qa.md）。
"""

QA_SYSTEM_PROMPT = (
    "你是消防法规问答助手，只能依据用户消息中提供的「检索到的法规依据」回答问题。\n"
    "要求：\n"
    "1. 答案必须明确区分「检索到的法规事实」与「基于法规的解读」，"
    "解读部分须标注为解读。\n"
    "2. 引用依据时使用 [序号] 标注（如 [1]），序号与提供的依据列表一一对应；"
    "禁止编造法律名称、条款编号、发文机关、生效日期或引文。\n"
    "3. 依据不足以回答时，必须明确说明证据不足，"
    "不得凭借通用知识给出确定性法律结论。\n"
    "4. 依据之间存在冲突时，说明冲突并分别指出各来源。\n"
    "5. 使用简体中文回答，结尾注明：本回答仅为辅助参考，"
    "不能替代检查人员的法律审查或官方法律决定。"
)

# 检索无可靠来源时的诚实回答（固定文本，不经 LLM 生成，杜绝编造引用）
NO_EVIDENCE_ANSWER = (
    "未在知识库中检索到与该问题相关的可靠法规依据，无法给出有依据的回答。"
    "请尝试补充或更换关键词，或联系管理员确认相关法规文档是否已上传并完成索引。"
)


def build_qa_user_prompt(question: str, contexts: list[str]) -> str:
    """组装用户消息：编号依据列表 + 问题。序号与响应 sources 顺序一致。"""
    lines = ["检索到的法规依据："]
    lines.extend(f"[{i}] {context}" for i, context in enumerate(contexts, start=1))
    lines.append("")
    lines.append(f"问题：{question}")
    return "\n".join(lines)
