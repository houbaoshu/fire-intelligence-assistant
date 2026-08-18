"""内置插件：QA 回答免责说明（on_qa_answer）。

法规问答产出回答后，若回答未包含免责说明则追加标准免责文本
（specs/regulation-qa.md：答案不得替代法律审查）。已包含时不重复追加。
"""

from app.plugins.registry import Plugin

DISCLAIMER = (
    "免责声明：本回答仅为辅助参考，不能替代检查人员的法律审查或官方法律决定。"
)


def _on_qa_answer(context: dict) -> None:
    answer = context.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return
    if "辅助参考" in answer:
        return
    context["answer"] = answer.rstrip() + "\n\n" + DISCLAIMER


PLUGIN = Plugin(
    name="qa_disclaimer",
    version="1.0.0",
    description="法规问答回答缺失免责说明时追加标准免责声明（on_qa_answer）",
    hooks={"on_qa_answer": _on_qa_answer},
)
