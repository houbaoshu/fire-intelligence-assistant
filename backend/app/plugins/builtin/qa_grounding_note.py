"""Sample builtin plugin: appends a grounding disclaimer to QA answers.

Demonstrates the plugin contract: modules expose a PLUGIN dict with hooks.
"""


def _hook(payload: dict) -> dict:
    answer = payload.get("answer", "")
    if answer and "检索材料" not in answer[-200:]:
        payload["answer"] = (
            answer + "\n\n(本回答基于知识库检索材料生成,仅供参考,不构成法律意见。)"
        )
    return payload


PLUGIN = {
    "name": "qa_grounding_note",
    "version": "0.1.0",
    "description": "在法规问答回答末尾追加证据提示,强化'回答基于检索材料'的可信度。",
    "enabled": True,
    "hooks": {
        "qa_post_process": _hook,
    },
}
