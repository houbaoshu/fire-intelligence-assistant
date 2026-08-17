"""询问记录生成 Prompt（ARCHITECTURE.md §13 / specs/interview-record.md）。

约束来源：
- 不得虚构说话人、陈述、时间、地点、身份或承认事项；听不清的片段
  必须标注为「无法听清」，禁止静默猜测补齐（specs/interview-record.md）；
- 清理标点与口头语不得改变实质含义，不得把模糊陈述改写为更确定的陈述；
- 说话人标签一律使用中性标签（询问人/被询问人），无用户确认不得转为
  具体身份；
- 输出必须为结构化 JSON，解析失败按任务失败处理。
"""

INTERVIEW_CLEANUP_SYSTEM_PROMPT = (
    "你是询问录音转写整理助手。对用户提供的机器转写原文做最低限度清理："
    "修正明显错别字与标点、去除无意义口头语（如「嗯」「啊」）。\n"
    "严格要求：\n"
    "1. 不得改变任何陈述的实质含义；不得删除事实性内容；不得把模糊"
    "陈述改写为更确定的陈述。\n"
    "2. 无法听清或无法辨识的片段保留并标注为「（无法听清）」，"
    "禁止猜测补齐。\n"
    "3. 只输出一个 JSON 对象：{\"cleaned_transcript\": \"清理后的全文\"}，"
    "不要输出任何解释或 Markdown 标记。"
)

INTERVIEW_STRUCTURE_SYSTEM_PROMPT = (
    "你是消防询问笔录整理助手。根据用户提供的询问录音转写文本，"
    "产出结构化的询问记录草稿 JSON。\n"
    "严格要求：\n"
    "1. 不得虚构说话人、陈述、时间、地点、身份或承认事项；转写中没有"
    "的信息一律留空（空字符串或空数组）。\n"
    "2. 说话人一律使用中性标签「询问人」与「被询问人」；无法区分说话人"
    "时按问答语气推断，推断不出的内容不进入问答列表。\n"
    "3. questions_and_answers 中的每个问答必须可追溯到转写原文，"
    "保留原意，只做语句通顺化整理。\n"
    "4. interviewee_name / interviewer_names / location / 起止时间仅当"
    "转写中明确提及才可填写。\n"
    "5. 只输出一个 JSON 对象，不要输出任何解释、前缀或 Markdown 标记。"
)

INTERVIEW_STRUCTURE_OUTPUT_SCHEMA = """{
  "title": "记录标题，无依据时为空字符串",
  "interviewee_name": "被询问人姓名，转写未提及为空字符串",
  "interviewer_names": ["询问人姓名", "转写未提及为空数组"],
  "location": "询问地点，转写未提及为空字符串",
  "started_at": "开始时间，格式 YYYY-MM-DDTHH:MM，转写未提及为空字符串",
  "ended_at": "结束时间，格式 YYYY-MM-DDTHH:MM，转写未提及为空字符串",
  "questions_and_answers": [
    {"question": "询问人的问题（中性标签整理）", "answer": "被询问人的回答"}
  ]
}"""


def build_interview_cleanup_user_prompt(transcript: str) -> str:
    return "机器转写原文如下：\n" + transcript


def build_interview_structure_user_prompt(
    *, transcript: str, remarks: str | None
) -> str:
    sections = ["询问录音转写文本如下：", transcript, ""]
    sections.append("【检查人员备注】（人工输入，与转写内容区分）")
    sections.append(remarks or "（无）")
    sections.append("")
    sections.append("请输出符合以下形状的单个 JSON 对象（无依据的字段留空）：")
    sections.append(INTERVIEW_STRUCTURE_OUTPUT_SCHEMA)
    return "\n".join(sections)
