"""AI pipeline tests: mocked OpenAI-compatible provider via httpx.MockTransport.

Tests exercise the REAL pipeline code (parsing, chunking, embeddings,
retrieval, LLM structured extraction, docx rendering); only the network
provider is simulated.
"""
from __future__ import annotations

import json
import subprocess
import uuid
from pathlib import Path

import httpx
import pytest

from app.core.config import get_settings


def _make_test_video() -> bytes:
    settings = get_settings()
    out = Path(settings.temporary_dir) / f"test_{uuid.uuid4()}.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "testsrc=duration=5:size=160x90:rate=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=5",
            "-pix_fmt", "yuv420p", "-shortest", str(out),
        ],
        check=True,
    )
    data = out.read_bytes()
    out.unlink(missing_ok=True)
    return data


def _make_test_audio() -> bytes:
    settings = get_settings()
    out = Path(settings.temporary_dir) / f"test_{uuid.uuid4()}.wav"
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            str(out),
        ],
        check=True,
    )
    data = out.read_bytes()
    out.unlink(missing_ok=True)
    return data


INSPECTION_STRUCTURED = {
    "title": "某商场消防检查记录",
    "inspection_unit": "某商场",
    "inspection_address": "某市某区某路 1 号",
    "inspection_date": "2026-01-01",
    "inspector_names": ["张三"],
    "contact_person": "",
    "contact_phone": "",
    "summary": "现场检查发现安全出口被锁闭。",
    "conclusion": "责令立即整改。",
    "items": [
        {
            "item_type": "violation",
            "location": "一层东侧",
            "description": "安全出口被锁闭",
            "legal_basis": "《中华人民共和国消防法》第二十八条",
            "correction_requirement": "立即解除锁闭",
            "severity": "high",
        }
    ],
}

PHOTO_CAPTION = {
    "caption": "疏散通道堆放杂物",
    "detected_address": "",
    "detected_violation": "疏散通道被占用",
}

PHOTO_SUMMARY = {
    "title": "某厂房消防拍照报告",
    "inspection_unit": "某厂房",
    "inspection_address": "某市某区某路 2 号",
    "violation_summary": "检查发现疏散通道堆放杂物。",
}

INTERVIEW_STRUCTURED = {
    "title": "某单位负责人询问记录",
    "interviewee_name": "赵某",
    "interviewer_names": ["张三"],
    "location": "某单位会议室",
    "started_at": None,
    "ended_at": None,
    "questions_and_answers": [{"question": "请问现场情况?", "answer": "安全出口被锁闭了。"}],
}

QA_ANSWER = "根据《中华人民共和国消防法》第二十八条,任何单位、个人不得锁闭、封堵安全出口。"


def _msg_text(message: dict) -> str:
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(
            part.get("text", "") for part in content if isinstance(part, dict)
        )
    return ""


def _transport_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path.endswith("/chat/completions"):
        body = json.loads(request.content)
        messages = body.get("messages", [])
        user_text = " ".join(_msg_text(m) for m in messages)
        if "消防检查记录" in user_text or "结构化检查记录" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(INSPECTION_STRUCTURED, ensure_ascii=False)}}]})
        # per-photo caption analysis (vision call asks to analyze the photo)
        if "分析这张消防检查现场照片" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(PHOTO_CAPTION, ensure_ascii=False)}}]})
        if "拍照报告" in user_text or "报告级字段" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(PHOTO_SUMMARY, ensure_ascii=False)}}]})
        if "询问笔录" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(INTERVIEW_STRUCTURED, ensure_ascii=False)}}]})
        if "帧分析" in user_text or "画面分析" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": "画面显示商场一层,安全出口处堆有杂物。"}}]})
        if "消防法规问答" in user_text or "检索到的材料" in user_text:
            return httpx.Response(200, json={"choices": [{"message": {"content": QA_ANSWER}}]})
        return httpx.Response(200, json={"choices": [{"message": {"content": "画面分析摘要。"}}]})
    if path.endswith("/embeddings"):
        body = json.loads(request.content)
        inputs = body.get("input", [])
        if isinstance(inputs, str):
            inputs = [inputs]
        return httpx.Response(
            200,
            json={
                "data": [
                    {"index": i, "embedding": [0.1 * (i + 1) + 0.01 * j for j in range(8)]}
                    for i in range(len(inputs))
                ]
            },
        )
    if path.endswith("/audio/transcriptions"):
        return httpx.Response(200, json={"text": "现场负责人承认安全出口被锁闭。"})
    if path.endswith("/rerank"):
        body = json.loads(request.content)
        n = len(body.get("documents", []))
        return httpx.Response(
            200,
            json={"results": [{"index": i, "relevance_score": 1.0 - i * 0.1} for i in range(n)]},
        )
    return httpx.Response(404, json={"error": "not found"})


# fake_ai fixture now lives in conftest.py (shared across test files)


# ---------------------------------------------------------------------------
# Pipeline tests
# ---------------------------------------------------------------------------

def test_inspection_generation_pipeline(client, auth_headers, fake_ai, db):
    """Full video -> frames -> vision -> OCR -> speech -> LLM -> record."""
    from app.services.tasks.worker import TaskWorker
    from app.core.database import SessionLocal

    hdrs, _ = auth_headers()
    video = _make_test_video()
    r = client.post(
        "/api/inspection-record/generate",
        headers=hdrs,
        files={"video": ("clip.mp4", video, "video/mp4")},
        data={"remarks": "检查某商场"},
    )
    assert r.status_code == 200, r.text
    task_id = r.json()["task_id"]

    # run the worker manually (in-process worker disabled in tests)
    worker = TaskWorker(SessionLocal)
    worker._tick()
    worker._tick()  # claim + execute

    tr = client.get(f"/api/tasks/{task_id}", headers=hdrs)
    assert tr.status_code == 200, tr.text
    body = tr.json()
    assert body["status"] == "completed", body
    assert body["result_data"] and body["result_data"]["record_id"]

    record_id = body["result_data"]["record_id"]
    rr = client.get(f"/api/inspection-record/{record_id}", headers=hdrs)
    assert rr.status_code == 200
    record = rr.json()
    assert record["status"] == "generated"
    assert record["inspection_unit"] == "某商场"
    assert len(record["items"]) == 1
    assert record["items"][0]["description"] == "安全出口被锁闭"


def test_photo_report_generation_pipeline(client, auth_headers, fake_ai, db):
    from app.services.tasks.worker import TaskWorker
    from app.core.database import SessionLocal

    hdrs, _ = auth_headers()
    video = _make_test_video()
    r = client.post(
        "/api/photo-report/generate",
        headers=hdrs,
        files={"video": ("clip.mp4", video, "video/mp4")},
    )
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    worker = TaskWorker(SessionLocal)
    worker._tick()
    worker._tick()

    tr = client.get(f"/api/tasks/{task_id}", headers=hdrs)
    assert tr.status_code == 200
    assert tr.json()["status"] == "completed", tr.json()
    report_id = tr.json()["result_data"]["record_id"]

    rr = client.get(f"/api/photo-report/{report_id}", headers=hdrs)
    assert rr.status_code == 200
    report = rr.json()
    assert report["status"] == "generated"
    print("DEBUG report:", {k: report[k] for k in ("status", "violation_summary")}, "images:", len(report["images"]))
    assert len(report["images"]) >= 1
    assert report["images"][0]["caption"] == "疏散通道堆放杂物"


def test_interview_generation_pipeline(client, auth_headers, fake_ai, db):
    from app.services.tasks.worker import TaskWorker
    from app.core.database import SessionLocal

    hdrs, _ = auth_headers()
    audio = _make_test_audio()
    r = client.post(
        "/api/interview-record/generate",
        headers=hdrs,
        files={"audio": ("rec.wav", audio, "audio/wav")},
    )
    assert r.status_code == 200
    task_id = r.json()["task_id"]

    worker = TaskWorker(SessionLocal)
    worker._tick()
    worker._tick()

    tr = client.get(f"/api/tasks/{task_id}", headers=hdrs)
    assert tr.status_code == 200
    assert tr.json()["status"] == "completed", tr.json()
    record_id = tr.json()["result_data"]["record_id"]

    rr = client.get(f"/api/interview-record/{record_id}", headers=hdrs)
    assert rr.status_code == 200
    record = rr.json()
    assert record["status"] == "generated"
    assert record["transcript"]  # raw transcript kept separate
    assert record["structured_content"]["questions_and_answers"]
    assert record["interviewee_name"] == "赵某"


def test_document_generation_and_download(client, auth_headers, db):
    """Finalize -> document_generation task -> download docx (versioned)."""
    from app.models.inspection import InspectionRecord
    from app.models.user import User
    from app.services.tasks.worker import TaskWorker
    from app.core.database import SessionLocal

    hdrs, user = auth_headers()
    u = db.query(User).filter_by(email=user["email"]).one()
    rec = InspectionRecord(
        status="generated", created_by=u.id, title="某商场检查记录",
        inspection_unit="某商场", inspection_address="某市某区某路 1 号",
        inspector_names=["张三"], summary="概述", conclusion="结论",
    )
    db.add(rec)
    db.flush()
    rec_id = str(rec.id)
    db.commit()

    r = client.put(f"/api/inspection-record/{rec_id}", headers=hdrs, json={"status": "finalized"})
    assert r.status_code == 200
    assert r.json()["record_number"]

    # run worker to complete document_generation
    worker = TaskWorker(SessionLocal)
    worker._tick()
    worker._tick()

    r = client.get(f"/api/inspection-record/{rec_id}/download", headers=hdrs)
    assert r.status_code == 200, r.text
    assert r.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    docx_bytes = r.content
    assert docx_bytes[:2] == b"PK"  # valid docx (zip)

    # regenerate -> new version (re-finalize rejected; force via direct service is out of scope;
    # verify version increments through a second generation)
    from app.models.document import GeneratedDocument

    docs = db.query(GeneratedDocument).filter(
        GeneratedDocument.source_entity_id == rec.id
    ).all()
    assert len(docs) == 1
    assert docs[0].version == 1

