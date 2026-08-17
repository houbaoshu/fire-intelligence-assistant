"""询问记录测试（API.md §4.3）：generate（仅音频）、字段校验、download。"""

from .helpers import FAKE_MP4, FAKE_WAV, auth_headers, register, wait_task

BASE = "/api/interview-record"


def _generate(client, tokens) -> str:
    resp = client.post(
        f"{BASE}/generate",
        headers=auth_headers(tokens),
        files={"audio": ("interview.wav", FAKE_WAV, "audio/wav")},
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    wait_task(client, tokens, task_id)
    return task_id


def _record_id(client, tokens) -> str:
    resp = client.get(BASE, headers=auth_headers(tokens))
    items = resp.json()["items"]
    assert len(items) == 1
    return items[0]["id"]


def test_generate_with_audio(client):
    tokens = register(client)
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    resp = client.get(f"{BASE}/{record_id}", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"  # AI 未配置
    assert body["transcript"] is None
    assert body["structured_content"] is None


def test_generate_rejects_video_field(client):
    """v1 仅支持音频来源，不接受 video 字段（缺少必填 audio → 400）。"""
    tokens = register(client)
    resp = client.post(
        f"{BASE}/generate",
        headers=auth_headers(tokens),
        files={"video": ("check.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_generate_rejects_wrong_audio_type(client):
    tokens = register(client)
    resp = client.post(
        f"{BASE}/generate",
        headers=auth_headers(tokens),
        files={"audio": ("song.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_update_fields(client):
    tokens = register(client)
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={
            "title": "某单位负责人询问记录",
            "interviewee_name": "赵某",
            "interviewer_names": ["张三", "李四"],
            "location": "某单位会议室",
            "started_at": "2026-01-01T09:00:00Z",
            "ended_at": "2026-01-01T09:30:00Z",
            "transcript": "询问全程转写文本",
            "structured_content": {"questions_and_answers": [{"question": "当日值班安排？", "answer": "两人值班。"}]},
            "status": "reviewed",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["interviewee_name"] == "赵某"
    assert body["status"] == "reviewed"
    assert body["structured_content"]["questions_and_answers"][0]["question"] == "当日值班安排？"


def test_started_after_ended_rejected(client):
    tokens = register(client)
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={"started_at": "2026-01-01T10:00:00Z", "ended_at": "2026-01-01T09:00:00Z"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_finalized_update_returns_409(client):
    tokens = register(client)
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    resp = client.put(
        f"{BASE}/{record_id}", headers=auth_headers(tokens), json={"status": "finalized"}
    )
    assert resp.status_code == 200
    resp = client.put(
        f"{BASE}/{record_id}", headers=auth_headers(tokens), json={"title": "改"}
    )
    assert resp.status_code == 409


def test_download_renders_docx(client):
    tokens = register(client)
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    client.put(
        f"{BASE}/{record_id}",
        headers=auth_headers(tokens),
        json={
            "title": "某单位负责人询问记录",
            "interviewee_name": "赵某",
            "transcript": "转写原文",
            "structured_content": {"questions_and_answers": [{"question": "q", "answer": "a"}]},
        },
    )
    resp = client.get(f"{BASE}/{record_id}/download", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == (
        f'attachment; filename="interview-record-{record_id}.docx"'
    )
    assert resp.content[:2] == b"PK"

    import io

    from docx import Document

    text = "\n".join(p.text for p in Document(io.BytesIO(resp.content)).paragraphs)
    assert "赵某" in text
    assert "转写原文" in text


def test_ownership(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    _generate(client, tokens)
    record_id = _record_id(client, tokens)
    resp = client.get(f"{BASE}/{record_id}", headers=auth_headers(other))
    assert resp.status_code == 404
    resp = client.get(BASE, headers=auth_headers(other))
    assert resp.json()["total"] == 0
