"""三条生成管线端到端测试（M4）。

外部 AI HTTP 调用全部 mock 为返回固定结构化结果的假服务对象
（monkeypatch 管线模块中的服务类）；ffmpeg 进程与 docx 渲染为真实执行。
覆盖：任务 completed → 记录 status=generated → 字段/items/images/
structured_content 落库 → record_number 生成 → download 打通 docx 渲染；
以及 LLM 非法 JSON → 任务 failed 的错误路径。
"""

import json
import re

from app.core.config import Settings
from app.services.ai.providers import AIProviders

from .helpers import (
    auth_headers,
    make_test_video_bytes,
    make_test_wav_bytes,
    register,
    wait_task,
)

INSPECTION_LLM_JSON = {
    "title": "某商场消防检查记录",
    "inspection_unit": "某商场",
    "inspection_address": "某市某区某路1号",
    "inspection_date": "2026-08-01",
    "inspector_names": ["张三", "李四"],
    "contact_person": "王五",
    "contact_phone": "13800000000",
    "summary": "检查发现一处隐患",
    "conclusion": "需限期整改",
    "items": [
        {
            "item_type": "violation",
            "location": "一层东侧",
            "description": "安全出口被锁闭",
            "legal_basis": "《中华人民共和国消防法》第二十八条（需人工复核）",
            "correction_requirement": "立即解除锁闭",
            "severity": "high",
        }
    ],
}

PHOTO_FRAME_JSON = {
    "detected_address": "某市某区某路1号",
    "detected_violation": "灭火器压力不足",
    "description": "通道内灭火器箱",
}

PHOTO_LLM_JSON = {
    "title": "某商场拍照报告",
    "inspection_unit": "某商场",
    "inspection_address": "某市某区某路1号",
    "violation_summary": "发现灭火器压力不足",
    "captions": [{"frame_index": 0, "caption": "一层通道灭火器压力不足"}],
}

INTERVIEW_STRUCTURE_JSON = {
    "title": "询问记录",
    "interviewee_name": "王五",
    "interviewer_names": ["张三"],
    "location": "会议室",
    "started_at": "",
    "ended_at": "",
    "questions_and_answers": [
        {"question": "事发时你在哪里？", "answer": "我在一层值班室。"}
    ],
}

RAW_TRANSCRIPT = "问：事发时你在哪里？答：我在一层值班室。"
CLEAN_TRANSCRIPT = "问：事发时你在哪里？\n答：我在一层值班室。"


class FakeVision:
    def __init__(self, payload=None, fail_calls: set[int] | None = None) -> None:
        self._text = json.dumps(payload or PHOTO_FRAME_JSON, ensure_ascii=False)
        self._fail_calls = fail_calls or set()
        self._calls = 0

    def analyze_image(self, prompt, *, image_bytes=None, image_url=None, **kwargs):
        self._calls += 1
        if self._calls in self._fail_calls:
            raise RuntimeError("vision boom")
        return self._text


class FakeOCR:
    def extract_text(self, image_bytes):
        return "安全出口 标识牌"


class FakeSpeech:
    def __init__(self, text: str = RAW_TRANSCRIPT) -> None:
        self._text = text

    def transcribe(self, audio_bytes, *, filename="audio.wav"):
        return self._text


class FakeLLM:
    """按 system prompt 分发固定结构化输出；payload 可注入非法 JSON。"""

    def __init__(self, payload=None) -> None:
        self._payload = payload

    def chat(self, messages, *, temperature=0.2):
        if self._payload is not None:
            return self._payload
        system = messages[0]["content"]
        if "清洗" in system or "清理" in system:
            return json.dumps({"cleaned_transcript": CLEAN_TRANSCRIPT}, ensure_ascii=False)
        if "拍照报告" in system:
            return json.dumps(PHOTO_LLM_JSON, ensure_ascii=False)
        if "笔录" in system:
            return json.dumps(INTERVIEW_STRUCTURE_JSON, ensure_ascii=False)
        return json.dumps(INSPECTION_LLM_JSON, ensure_ascii=False)


def _configured_providers() -> AIProviders:
    settings = Settings(
        AI_LLM_API_KEY="k", AI_LLM_MODEL="m", AI_LLM_BASE_URL="http://x",
        AI_VISION_API_KEY="k", AI_VISION_MODEL="m", AI_VISION_BASE_URL="http://x",
        AI_OCR_API_KEY="k", AI_OCR_MODEL="m", AI_OCR_BASE_URL="http://x",
        AI_SPEECH_API_KEY="k", AI_SPEECH_MODEL="m", AI_SPEECH_BASE_URL="http://x",
    )
    return AIProviders(settings)


def _patch_common(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.tasks.worker.get_ai_providers", _configured_providers
    )


def _generate(client, tokens, url, field, filename, content, mime):
    resp = client.post(
        url,
        headers=auth_headers(tokens),
        files={field: (filename, content, mime)},
        data={"remarks": "现场补充说明"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["task_id"]


# ---------- 检查记录 ----------


def test_inspection_pipeline_end_to_end(client, monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        "app.services.pipelines.inspection.VisionService", lambda: FakeVision()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.OCRService", lambda: FakeOCR()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.SpeechService", lambda: FakeSpeech()
    )
    monkeypatch.setattr("app.services.pipelines.inspection.LLMService", lambda: FakeLLM())

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/inspection-record/generate",
        "video", "scene.mp4", make_test_video_bytes(seconds=3), "video/mp4",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "completed", task
    assert task["progress"] == 100

    record_id = task["result_data"]["record_id"]
    detail = client.get(
        f"/api/inspection-record/{record_id}", headers=auth_headers(tokens)
    ).json()
    assert detail["status"] == "generated"
    assert re.fullmatch(r"JC-\d{4}-\d{4}", detail["record_number"])
    assert detail["inspection_unit"] == "某商场"
    assert detail["inspection_address"] == "某市某区某路1号"
    assert detail["inspector_names"] == ["张三", "李四"]
    assert detail["inspection_date"].startswith("2026-08-01")
    assert detail["source_task_id"] == task_id
    assert len(detail["items"]) == 1
    item = detail["items"][0]
    assert item["item_type"] == "violation"
    assert item["severity"] == "high"
    assert item["description"] == "安全出口被锁闭"

    # M2 渲染链路与新数据打通：download 得到 docx，文件名带 record_number
    resp = client.get(
        f"/api/inspection-record/{record_id}/download", headers=auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"
    assert detail["record_number"] in resp.headers["Content-Disposition"]


def test_inspection_pipeline_invalid_llm_json_fails_readably(client, monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        "app.services.pipelines.inspection.VisionService", lambda: FakeVision()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.OCRService", lambda: FakeOCR()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.SpeechService", lambda: FakeSpeech()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.LLMService",
        lambda: FakeLLM(payload="这不是 JSON"),
    )

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/inspection-record/generate",
        "video", "scene.mp4", make_test_video_bytes(seconds=3), "video/mp4",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "failed"
    assert task["error_code"] == "AI_OUTPUT_INVALID"
    assert "无法解析" in task["error_message"]

    # 关联记录同步置 failed
    records = client.get("/api/inspection-record", headers=auth_headers(tokens)).json()
    assert records["items"][0]["status"] == "failed"


def test_inspection_pipeline_partial_vision_failure_degrades(client, monkeypatch):
    _patch_common(monkeypatch)
    # 直通筛选，保证两帧都进入视觉分析（去重行为已由 test_media 覆盖）
    monkeypatch.setattr(
        "app.services.pipelines.inspection.select_key_frames",
        lambda frames, max_frames: (frames, []),
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.VisionService",
        lambda: FakeVision(fail_calls={2}),  # 第二帧分析失败
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.OCRService", lambda: FakeOCR()
    )
    monkeypatch.setattr(
        "app.services.pipelines.inspection.SpeechService", lambda: FakeSpeech()
    )
    monkeypatch.setattr("app.services.pipelines.inspection.LLMService", lambda: FakeLLM())

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/inspection-record/generate",
        "video", "scene.mp4", make_test_video_bytes(seconds=3), "video/mp4",
    )
    task = wait_task(client, tokens, task_id)
    # 部分失败不阻断任务：completed 且 warnings 可见（不静默）
    assert task["status"] == "completed"
    assert task["result_data"]["warnings"]
    assert any("视觉分析失败" in w for w in task["result_data"]["warnings"])


# ---------- 拍照报告 ----------


def test_photo_report_pipeline_end_to_end(client, monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr("app.services.pipelines.photo.VisionService", lambda: FakeVision())
    monkeypatch.setattr("app.services.pipelines.photo.OCRService", lambda: FakeOCR())
    monkeypatch.setattr("app.services.pipelines.photo.LLMService", lambda: FakeLLM())

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/photo-report/generate",
        "video", "scene.mp4", make_test_video_bytes(seconds=3), "video/mp4",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "completed", task

    report_id = task["result_data"]["record_id"]
    detail = client.get(
        f"/api/photo-report/{report_id}", headers=auth_headers(tokens)
    ).json()
    assert detail["status"] == "generated"
    assert detail["title"] == "某商场拍照报告"
    assert detail["violation_summary"] == "发现灭火器压力不足"
    assert len(detail["images"]) >= 1
    image = detail["images"][0]
    assert image["is_selected"] is True
    assert isinstance(image["frame_timestamp"], float)
    assert image["detected_address"] == "某市某区某路1号"
    assert image["detected_violation"] == "灭火器压力不足"
    # 首帧有 LLM caption（frame_index=0）
    assert image["caption"] == "一层通道灭火器压力不足"

    # 关键帧已登记 uploaded_files 且 docx 渲染可读取
    resp = client.get(
        f"/api/photo-report/{report_id}/download", headers=auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"


# ---------- 询问记录 ----------


def test_interview_pipeline_end_to_end(client, monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        "app.services.pipelines.interview.SpeechService", lambda: FakeSpeech()
    )
    monkeypatch.setattr("app.services.pipelines.interview.LLMService", lambda: FakeLLM())

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/interview-record/generate",
        "audio", "interview.wav", make_test_wav_bytes(seconds=2), "audio/wav",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "completed", task

    record_id = task["result_data"]["record_id"]
    detail = client.get(
        f"/api/interview-record/{record_id}", headers=auth_headers(tokens)
    ).json()
    assert detail["status"] == "generated"
    assert detail["interviewee_name"] == "王五"
    assert detail["interviewer_names"] == ["张三"]
    # 原始转写与结构化内容分开保存（契约）
    assert detail["transcript"] == CLEAN_TRANSCRIPT
    structured = detail["structured_content"]
    assert structured["raw_transcript"] == RAW_TRANSCRIPT
    assert structured["questions_and_answers"] == [
        {"question": "事发时你在哪里？", "answer": "我在一层值班室。"}
    ]

    resp = client.get(
        f"/api/interview-record/{record_id}/download", headers=auth_headers(tokens)
    )
    assert resp.status_code == 200
    assert resp.content[:2] == b"PK"


def test_interview_pipeline_empty_transcript_fails(client, monkeypatch):
    """无可辨识语音：任务失败且错误可读，禁止编造 transcript。"""
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        "app.services.pipelines.interview.SpeechService", lambda: FakeSpeech(text="")
    )
    monkeypatch.setattr("app.services.pipelines.interview.LLMService", lambda: FakeLLM())

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/interview-record/generate",
        "audio", "interview.wav", make_test_wav_bytes(seconds=2), "audio/wav",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "failed"
    assert task["error_code"] == "NO_SPEECH_CONTENT"


def test_interview_pipeline_invalid_llm_json_fails_readably(client, monkeypatch):
    _patch_common(monkeypatch)
    monkeypatch.setattr(
        "app.services.pipelines.interview.SpeechService", lambda: FakeSpeech()
    )
    monkeypatch.setattr(
        "app.services.pipelines.interview.LLMService",
        lambda: FakeLLM(payload="{broken"),
    )

    tokens = register(client)
    task_id = _generate(
        client, tokens, "/api/interview-record/generate",
        "audio", "interview.wav", make_test_wav_bytes(seconds=2), "audio/wav",
    )
    task = wait_task(client, tokens, task_id)
    assert task["status"] == "failed"
    # 清洗阶段失败会降级为原文继续；结构化阶段非法 JSON 必须任务失败
    assert task["error_code"] == "AI_OUTPUT_INVALID"
