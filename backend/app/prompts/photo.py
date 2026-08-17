"""拍照报告生成 Prompt（ARCHITECTURE.md §12 / specs/photo-report.md）。

约束来源：
- 系统绝不得编造地址、违规、设备或地点；证据冲突或不完整时留空并
  转人工复核（specs/photo-report.md 地址一致性 / 违规描述规则）；
- 每张照片至多描述一个主要违规；caption 简洁、客观、写实；
- 输出必须为结构化 JSON，解析失败按任务失败处理。
"""

PHOTO_FRAME_ANALYSIS_PROMPT = (
    "你是消防检查现场的图像分析助手。分析这一张从检查视频中抽取的帧，"
    "只输出一个 JSON 对象，不要输出任何解释或 Markdown 标记：\n"
    "{\n"
    '  "detected_address": "画面中可辨识的地址文字（如门牌、招牌），'
    '无法辨识时为空字符串",\n'
    '  "detected_violation": "画面中清晰可见的最主要的一处消防违规或隐患，'
    '无可见违规时为空字符串",\n'
    '  "description": "对画面内容的客观描述（一到两句）"\n'
    "}\n"
    "严格要求：只描述画面中真实可见的内容；禁止推测、编造地址或违规；"
    "多个互不相关的问题只选最主要的一项。"
)

PHOTO_REPORT_SYSTEM_PROMPT = (
    "你是消防检查拍照报告整理助手。根据用户提供的逐帧图像分析结果、"
    "帧内 OCR 文字与检查人员备注，产出报告级结构化 JSON 与每张图片的"
    "caption 草稿。\n"
    "严格要求：\n"
    "1. 只依据提供的证据填写；无证据字段留空，禁止编造单位、地址或违规。\n"
    "2. 报告地址在全文保持一致；各帧地址证据冲突时 inspection_address "
    "留空并在 violation_summary 中标注「地址证据冲突，需人工复核」。\n"
    "3. 每条 caption 只描述该帧可见的主要问题，简洁、客观、写实，"
    "不拼凑无依据或互不相关的违规，长度不超过 80 字。\n"
    "4. 只输出一个 JSON 对象，不要输出任何解释、前缀或 Markdown 标记。"
)

PHOTO_REPORT_OUTPUT_SCHEMA = """{
  "title": "报告标题，无证据时为空字符串",
  "inspection_unit": "被检查单位，无证据时为空字符串",
  "inspection_address": "检查地址（各帧证据一致时填写），否则为空字符串",
  "violation_summary": "违规情况摘要，无可见违规时说明未识别到违规",
  "captions": [
    {"frame_index": 0, "caption": "该帧图片说明（frame_index 与输入帧序号一致）"}
  ]
}"""


def build_photo_report_user_prompt(
    *,
    frame_results: list[dict],
    remarks: str | None,
) -> str:
    """组装用户消息：逐帧分析结果（含 frame_index/时间戳/OCR）+ 输出约束。"""
    import json

    sections = ["以下是逐帧图像分析结果（frame_index 为帧序号，timestamp 单位：秒）："]
    sections.append(json.dumps(frame_results, ensure_ascii=False, indent=2))
    sections.append("")
    sections.append("【检查人员备注】（人工输入，与 AI 证据区分）")
    sections.append(remarks or "（无）")
    sections.append("")
    sections.append("请输出符合以下形状的单个 JSON 对象（无证据的字段留空）：")
    sections.append(PHOTO_REPORT_OUTPUT_SCHEMA)
    return "\n".join(sections)
