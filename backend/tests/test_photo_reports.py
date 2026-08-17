"""拍照报告测试（API.md §4.2）：generate、images 逐项更新、download 409/渲染。"""

import io
import uuid

from .helpers import FAKE_MP4, FAKE_PNG, auth_headers, make_role, register, wait_task

BASE = "/api/photo-report"


def _generate(client, tokens) -> str:
    resp = client.post(
        f"{BASE}/generate",
        headers=auth_headers(tokens),
        files={"video": ("check.mp4", FAKE_MP4, "video/mp4")},
    )
    assert resp.status_code == 200, resp.text
    task_id = resp.json()["task_id"]
    wait_task(client, tokens, task_id)
    return task_id


def _report_id(client, tokens) -> str:
    resp = client.get(BASE, headers=auth_headers(tokens))
    items = resp.json()["items"]
    assert len(items) == 1
    return items[0]["id"]


def _attach_image(report_id: str, caption: str = "疏散通道堆放杂物") -> str:
    """直接写入一条带真实 PNG 存储的报告图片（模拟 M4 管线产出）。"""
    from app.db import SessionLocal
    from app.models.photo_report import PhotoReportImage
    from app.services.file_service import FileService

    session = SessionLocal()
    try:
        files = FileService(session)
        uploaded = files.save_upload(
            filename="frame.png",
            content_type="image/png",
            data=FAKE_PNG,
            category="image",
            uploaded_by=_report_owner(session, report_id),
        )
        image = PhotoReportImage(
            photo_report_id=uuid.UUID(report_id),
            uploaded_file_id=uploaded.id,
            frame_timestamp=12.5,
            caption=caption,
            is_selected=True,
            sort_order=1,
        )
        session.add(image)
        session.commit()
        return str(image.id)
    finally:
        session.close()


def _report_owner(session, report_id: str):
    from app.models.photo_report import PhotoReport

    return session.get(PhotoReport, uuid.UUID(report_id)).created_by


def test_generate_and_detail(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    resp = client.get(f"{BASE}/{report_id}", headers=auth_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "failed"
    assert body["images"] == []
    assert body["source_task_id"]


def test_update_report_fields(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    resp = client.put(
        f"{BASE}/{report_id}",
        headers=auth_headers(tokens),
        json={"title": "某厂房消防拍照报告", "violation_summary": "隐患概述", "status": "draft"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "某厂房消防拍照报告"


def test_update_images_by_id_only_editable_fields(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    image_id = _attach_image(report_id)

    resp = client.put(
        f"{BASE}/{report_id}",
        headers=auth_headers(tokens),
        json={"images": [{"id": image_id, "caption": "修订后的说明", "is_selected": False, "sort_order": 2}]},
    )
    assert resp.status_code == 200, resp.text
    image = resp.json()["images"][0]
    assert image["caption"] == "修订后的说明"
    assert image["is_selected"] is False
    assert image["sort_order"] == 2
    assert image["frame_timestamp"] == 12.5  # 不可编辑字段保持不变


def test_update_image_with_foreign_id_rejected(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    resp = client.put(
        f"{BASE}/{report_id}",
        headers=auth_headers(tokens),
        json={"images": [{"id": str(uuid.uuid4()), "caption": "x"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "VALIDATION_ERROR"


def test_download_without_selected_images_returns_409(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    resp = client.get(f"{BASE}/{report_id}/download", headers=auth_headers(tokens))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "DOCUMENT_NOT_READY"
    assert resp.json()["error"]["message"]


def test_download_with_selected_image_embeds_png(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    _attach_image(report_id)
    client.put(
        f"{BASE}/{report_id}",
        headers=auth_headers(tokens),
        json={"title": "某厂房消防拍照报告"},
    )
    resp = client.get(f"{BASE}/{report_id}/download", headers=auth_headers(tokens))
    assert resp.status_code == 200
    assert resp.headers["content-disposition"] == (
        f'attachment; filename="photo-report-{report_id}.docx"'
    )
    assert resp.content[:2] == b"PK"
    # 图片嵌入文档（zip 内含媒体文件）
    import zipfile

    names = zipfile.ZipFile(io.BytesIO(resp.content)).namelist()
    assert any(n.startswith("word/media/") for n in names)


def test_unselected_image_excluded_from_document(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    image_id = _attach_image(report_id)
    # 取消选中后无有效图片 → 409
    resp = client.put(
        f"{BASE}/{report_id}",
        headers=auth_headers(tokens),
        json={"images": [{"id": image_id, "is_selected": False}]},
    )
    assert resp.status_code == 200
    resp = client.get(f"{BASE}/{report_id}/download", headers=auth_headers(tokens))
    assert resp.status_code == 409


def test_finalized_report_update_returns_409(client):
    tokens = register(client)
    _generate(client, tokens)
    report_id = _report_id(client, tokens)
    # 定稿需 record.finalize 权限（M6：supervisor/admin）
    make_role(tokens["user"]["id"], "supervisor")
    resp = client.put(
        f"{BASE}/{report_id}", headers=auth_headers(tokens), json={"status": "finalized"}
    )
    assert resp.status_code == 200
    resp = client.put(
        f"{BASE}/{report_id}", headers=auth_headers(tokens), json={"title": "改"}
    )
    assert resp.status_code == 409


def test_ownership_and_pagination(client):
    tokens = register(client)
    other = register(client, email="other@example.com")
    _generate(client, tokens)
    report_id = _report_id(client, tokens)

    resp = client.get(f"{BASE}/{report_id}", headers=auth_headers(other))
    assert resp.status_code == 404
    resp = client.get(BASE, headers=auth_headers(other))
    assert resp.json()["total"] == 0

    resp = client.get(BASE, params={"page": 1, "page_size": 1}, headers=auth_headers(tokens))
    assert resp.json()["total"] == 1
    assert len(resp.json()["items"]) == 1
