"""Inspection / photo / interview record CRUD, update rules and document flow.

Generation pipelines require AI providers; those flows are tested in
test_ai_pipelines.py with a mocked provider transport.
"""
from __future__ import annotations


def _video_upload() -> dict:
    return {
        "files": {
            "video": (
                "clip.mp4",
                b"\x00\x00\x00\x18ftypmp42" + b"0" * 1000,
                "video/mp4",
            )
        }
    }


def test_inspection_generate_returns_task(client, auth_headers):
    hdrs, _ = auth_headers()
    r = client.post("/api/inspection-record/generate", headers=hdrs, **_video_upload())
    # task accepted; worker disabled in tests
    assert r.status_code == 200
    assert "task_id" in r.json()

    task_id = r.json()["task_id"]
    tr = client.get(f"/api/tasks/{task_id}", headers=hdrs)
    assert tr.status_code == 200
    assert tr.json()["task_type"] == "inspection_record_generation"


def test_generate_rejects_bad_file(client, auth_headers):
    hdrs, _ = auth_headers()
    r = client.post(
        "/api/inspection-record/generate",
        headers=hdrs,
        files={"video": ("bad.exe", b"MZ", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_FILE_TYPE"


def test_inspection_crud_and_finalize(client, auth_headers, db):
    from app.models.inspection import InspectionRecord
    from app.models.user import User

    hdrs, user = auth_headers()
    u = db.query(User).filter_by(email=user["email"]).one()
    rec = InspectionRecord(status="generated", created_by=u.id, title="某商场检查记录")
    db.add(rec)
    db.flush()
    rec_id = str(rec.id)
    db.commit()

    r = client.get(f"/api/inspection-record/{rec_id}", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["title"] == "某商场检查记录"

    r = client.get("/api/inspection-record", headers=hdrs)
    assert r.status_code == 200
    assert r.json()["total"] == 1

    r = client.put(
        f"/api/inspection-record/{rec_id}",
        headers=hdrs,
        json={
            "inspection_unit": "某商场",
            "inspection_address": "某市某区某路 1 号",
            "inspector_names": ["张三"],
            "items": [
                {
                    "item_type": "violation",
                    "location": "一层东侧",
                    "description": "安全出口被锁闭",
                    "legal_basis": "《中华人民共和国消防法》第二十八条",
                    "severity": "high",
                }
            ],
        },
    )
    assert r.status_code == 200, r.text
    assert len(r.json()["items"]) == 1

    # item replacement: drop items
    r = client.put(f"/api/inspection-record/{rec_id}", headers=hdrs, json={"items": []})
    assert r.status_code == 200
    assert r.json()["items"] == []

    # finalize
    r = client.put(f"/api/inspection-record/{rec_id}", headers=hdrs, json={"status": "finalized"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "finalized"
    assert body["record_number"].startswith("JC-")

    # finalized records reject content updates with 409
    r = client.put(f"/api/inspection-record/{rec_id}", headers=hdrs, json={"summary": "hack"})
    assert r.status_code == 409

    # download before document generation completes -> 409
    r = client.get(f"/api/inspection-record/{rec_id}/download", headers=hdrs)
    assert r.status_code == 409

    # other users cannot see the record
    hdrs2, _ = auth_headers()
    r = client.get(f"/api/inspection-record/{rec_id}", headers=hdrs2)
    assert r.status_code == 403


def test_interview_generate_rejects_video_only(client, auth_headers):
    hdrs, _ = auth_headers()
    r = client.post(
        "/api/interview-record/generate",
        headers=hdrs,
        files={"audio": ("rec.mp3", b"ID3\x04\x00\x00\x00", "audio/mpeg")},
    )
    assert r.status_code == 200

    r = client.post(
        "/api/interview-record/generate",
        headers=hdrs,
        files={"video": ("clip.mp4", b"\x00\x00\x00\x18ftypmp42", "video/mp4")},
    )
    # audio is required (v1 audio-only); missing -> 400 VALIDATION_ERROR
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_photo_report_crud(client, auth_headers, db):
    from app.models.photo_report import PhotoReport
    from app.models.user import User

    hdrs, user = auth_headers()
    u = db.query(User).filter_by(email=user["email"]).one()
    report = PhotoReport(status="generated", created_by=u.id, title="某厂房拍照报告")
    db.add(report)
    db.flush()
    report_id = str(report.id)
    db.commit()

    r = client.get(f"/api/photo-report/{report_id}", headers=hdrs)
    assert r.status_code == 200

    r = client.put(
        f"/api/photo-report/{report_id}",
        headers=hdrs,
        json={"inspection_unit": "某厂房", "violation_summary": "疏散通道堆放杂物", "status": "reviewed"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "reviewed"

    # finalize with no selected images -> validation error
    r = client.put(f"/api/photo-report/{report_id}", headers=hdrs, json={"status": "finalized"})
    assert r.status_code == 400
    assert "至少需要一张选中的图片" in r.json()["error"]["message"]


def test_audit_log_written_on_login(client, db):
    client.post("/api/auth/register", json={"email": "audit@test.com", "password": "password123"})
    client.post("/api/auth/login", json={"email": "audit@test.com", "password": "password123"})
    from app.models.audit import AuditLog

    entries = db.query(AuditLog).filter(AuditLog.action == "user.login").all()
    assert len(entries) >= 1
