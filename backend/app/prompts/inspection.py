"""检查记录生成 Prompt（ARCHITECTURE.md §11 / specs/inspection-record.md）。

约束来源：
- 禁止编造被检查单位、地址、人员、联系方式、日期、违法事实、法律依据
  或整改要求；缺失字段留空（specs/inspection-record.md 业务规则）；
- 法律依据仅可填写证据材料中明确出现的法规名称与条款，禁止凭模型
  印象作答（specs/_common.md AI 通用约束）；
- 低置信度结论标注需人工复核；
- 输出必须为结构化 JSON，解析失败按任务失败处理。
"""

INSPECTION_EXTRACT_SYSTEM_PROMPT = (
    "你是消防检查记录整理助手。根据用户提供的检查现场证据"
    "（视频帧视觉分析、帧内 OCR 文字、现场语音转写、检查人员备注），"
    "产出一份结构化的检查记录草稿 JSON。\n"
    "严格要求：\n"
    "1. 只依据提供的证据填写；任何没有证据支撑的字段必须留空（空字符串"
    "或空数组），绝对禁止编造单位名称、地址、人名、电话、日期、"
    "违法事实、法律依据或整改要求。\n"
    "2. 法律依据（legal_basis）仅当证据材料中明确出现法规名称或条款时"
    "才可填写，并注明「需人工复核」。\n"
    "3. 证据不足或相互矛盾的结论，在 summary 或 conclusion 中标注"
    "「需人工复核」。\n"
    "4. 检查人员备注是人工输入，优先级高于模型推断，但仍须与证据区分。\n"
    "5. 只输出一个 JSON 对象，不要输出任何解释、前缀或 Markdown 标记。"
)

# 输出 JSON 骨架（值仅为类型示例，提示模型输出形状；禁止照抄示例值）
INSPECTION_EXTRACT_OUTPUT_SCHEMA = """{
  "title": "记录标题，概括被检查单位与检查性质",
  "inspection_unit": "被检查单位名称，无证据时为空字符串",
  "inspection_address": "检查地址，无证据时为空字符串",
  "inspection_date": "检查日期，格式 YYYY-MM-DD，无证据时为空字符串",
  "inspector_names": ["检查人员姓名", "无证据时为空数组"],
  "contact_person": "联系人，无证据时为空字符串",
  "contact_phone": "联系电话，无证据时为空字符串",
  "summary": "检查情况概述",
  "conclusion": "检查结论",
  "items": [
    {
      "item_type": "violation | hazard | observation | compliant | recommendation",
      "location": "发现位置，无证据时为空字符串",
      "description": "发现描述（必填，无实质发现则不产出该条）",
      "legal_basis": "法律依据，仅证据明确出现时填写",
      "correction_requirement": "整改要求，无证据时为空字符串",
      "severity": "low | medium | high | critical，无法判断时为空字符串"
    }
  ]
}"""


def build_inspection_extract_user_prompt(
    *,
    frame_analyses: list[dict],
    ocr_texts: list[dict],
    transcript: str | None,
    remarks: str | None,
) -> str:
    """组装用户消息：分节的证据材料 + 输出 schema 约束。"""
    import json

    sections = ["以下是检查现场证据材料：", ""]
    sections.append("【视频帧视觉分析】（时间戳单位：秒）")
    sections.append(
        json.dumps(frame_analyses, ensure_ascii=False, indent=2)
        if frame_analyses
        else "（无）"
    )
    sections.append("")
    sections.append("【帧内 OCR 文字】")
    sections.append(
        json.dumps(ocr_texts, ensure_ascii=False, indent=2) if ocr_texts else "（无）"
    )
    sections.append("")
    sections.append("【现场语音转写】")
    sections.append(transcript or "（无）")
    sections.append("")
    sections.append("【检查人员备注】（人工输入，与 AI 证据区分）")
    sections.append(remarks or "（无）")
    sections.append("")
    sections.append("请输出符合以下形状的单个 JSON 对象（无证据的字段留空）：")
    sections.append(INSPECTION_EXTRACT_OUTPUT_SCHEMA)
    return "\n".join(sections)
