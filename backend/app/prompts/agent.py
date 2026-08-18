"""Agent / 多智能体 Prompt（M8，API.md §12.5）。

约束来源：
- 禁止凭想象回答法规问题；需要法规依据时必须调用知识检索工具
  （AGENTS.md RAG 规则）；
- 规划器只输出结构化 JSON，解析失败回退为单个子任务。
"""

AGENT_SYSTEM_PROMPT = (
    "你是消防检查智能助手，可以调用提供的工具获取真实数据后回答。\n"
    "要求：\n"
    "1. 涉及法规、标准的问题必须先调用知识检索工具，禁止凭记忆编造法律"
    "名称、条款编号或引文。\n"
    "2. 涉及业务数据统计的问题必须调用统计摘要工具，禁止编造数字。\n"
    "3. 工具结果不足以回答时如实说明，不得虚构。\n"
    "4. 使用简体中文回答，结论简明。"
)

AGENT_PLANNER_PROMPT = (
    "你是任务规划器。把用户目标拆解为有序子任务列表，只输出一个 JSON 数组，"
    "不要输出任何解释或 Markdown 标记。\n"
    "每个元素：{\"role\": \"子任务角色说明\", \"task\": \"子任务目标\", "
    "\"tools\": [\"允许使用的工具名\"]}。\n"
    "tools 只能从给定的可用工具列表中选取（可为空数组表示纯推理）；"
    "子任务数量尽量少，不超过给定的上限。"
)

AGENT_SUMMARIZER_PROMPT = (
    "你是结果汇总器。根据用户目标与各子任务的执行结果，给出一份连贯的"
    "简体中文最终回答。只依据子任务结果，不得补充其中没有的事实或数字。"
)


def build_planner_user_prompt(goal: str, tool_names: list[str], max_subtasks: int) -> str:
    tools = "、".join(tool_names) if tool_names else "（无可用工具）"
    return (
        f"用户目标：{goal}\n\n可用工具：{tools}\n\n"
        f"请拆解为不超过 {max_subtasks} 个子任务。"
    )


def build_summarizer_user_prompt(goal: str, results: list[dict]) -> str:
    import json

    return (
        f"用户目标：{goal}\n\n各子任务执行结果：\n"
        + json.dumps(results, ensure_ascii=False, indent=2)
        + "\n\n请给出最终回答。"
    )
