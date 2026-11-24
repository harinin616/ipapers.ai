"""Integration tests (mocked DB): auth enforcement, folder roles, upload validation, subscription ownership."""
import io
import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from tests.conftest import import_app

main = import_app()
from app.security import create_access_token  # noqa: E402
from app.services.db_service import db_service  # noqa: E402
from app.api import upload as upload_api  # noqa: E402

client = TestClient(main.app)

ALICE, BOB = str(uuid.uuid4()), str(uuid.uuid4())


def auth(uid):
    return {"Authorization": f"Bearer {create_access_token(uid)}"}


# ---------- authentication ----------
def test_guest_issues_working_token():
    r = client.post("/api/user/guest")
    assert r.status_code == 200
    body = r.json()
    assert body["user_id"] and body["access_token"]


def test_forged_header_without_token_is_401():
    assert client.get("/api/folders", headers={"X-User-ID": ALICE}).status_code == 401


def test_folder_list_uses_verified_identity_not_header(monkeypatch):
    seen = {}

    async def fake(uid):
        seen["uid"] = str(uid)
        return []

    monkeypatch.setattr(db_service, "get_folders_with_files", fake)
    r = client.get("/api/folders", headers={**auth(ALICE), "X-User-ID": BOB})
    assert r.status_code == 200 and seen["uid"] == ALICE


def test_public_paper_search_needs_no_token(monkeypatch):
    monkeypatch.setattr(db_service, "count_papers", AsyncMock(return_value=3))
    assert client.get("/api/papers/count").status_code == 200


# ---------- folder roles ----------
@pytest.mark.parametrize("method,path,need_role", [
    ("get", "/api/folders/7/files", "viewer"),
    ("get", "/api/folders/7/summary", "viewer"),
    ("post", "/api/folders/7/summary/regenerate", "editor"),
    ("post", "/api/folders/7/files", "editor"),
    ("delete", "/api/folders/7/files/abc", "editor"),
])
def test_folder_endpoints_enforce_roles(monkeypatch, method, path, need_role):
    monkeypatch.setattr(db_service, "get_files_by_folder_id", AsyncMock(return_value=[]))
    monkeypatch.setattr(db_service, "get_folder_summary", AsyncMock(return_value="s"))
    monkeypatch.setattr(db_service, "add_file_to_folder", AsyncMock(return_value=True))
    monkeypatch.setattr(db_service, "remove_file_from_folder", AsyncMock(return_value=True))
    kw = {"json": {"paper_id": "p", "platform": "arxiv"}} if method == "post" and path.endswith("/files") else {}

    def call(role):
        monkeypatch.setattr(db_service, "get_folder_role", AsyncMock(return_value=role))
        return getattr(client, method)(path, headers=auth(BOB), **kw)

    assert call(None).status_code == 404            # no access: existence hidden
    if need_role == "editor":
        assert call("viewer").status_code == 403    # too low
        assert call("editor").status_code != 403
    assert call("owner").status_code not in (401, 403, 404)


def test_folder_access_requires_login():
    assert client.get("/api/folders/7/files").status_code == 401


# ---------- upload validation ----------
def _upload(content: bytes, name="p.pdf"):
    return client.post("/api/upload/", headers=auth(ALICE), files={"file": (name, io.BytesIO(content), "application/pdf")})


def test_upload_requires_auth():
    r = client.post("/api/upload/", files={"file": ("p.pdf", io.BytesIO(b"%PDF-1.4 x"), "application/pdf")})
    assert r.status_code == 401


def test_upload_rejects_non_pdf_content_with_pdf_name():
    assert _upload(b"MZ\x90\x00 not a pdf").status_code == 415


def test_upload_rejects_wrong_extension():
    assert _upload(b"%PDF-1.4 data", name="x.exe").status_code == 400


def test_upload_rejects_oversize(monkeypatch):
    monkeypatch.setattr(upload_api, "MAX_UPLOAD_BYTES", 1024)
    before = set(__import__("os").listdir(upload_api.UPLOAD_DIR))
    assert _upload(b"%PDF-1.4" + b"0" * 4096).status_code == 413
    assert set(__import__("os").listdir(upload_api.UPLOAD_DIR)) == before  # partial file removed


# ---------- subscription ownership ----------
def test_subscription_requires_login():
    assert client.get("/api/user/subscription-status", params={"email": "a@b.c"}).status_code == 401


def test_subscription_only_own_email(monkeypatch):
    monkeypatch.setattr(db_service, "get_user_email", AsyncMock(return_value="alice@example.com"))
    monkeypatch.setattr(db_service, "check_email_in_list", AsyncMock(return_value=True))
    assert client.get("/api/user/subscription-status", params={"email": "victim@example.com"}, headers=auth(ALICE)).status_code == 403
    ok = client.get("/api/user/subscription-status", params={"email": "Alice@Example.com"}, headers=auth(ALICE))
    assert ok.status_code == 200
    r = client.post("/api/user/subscription", json={"email": "victim@example.com", "subscribed": False}, headers=auth(ALICE))
    assert r.status_code == 403


# ---------- CORS ----------
def test_cors_not_wildcard():
    r = client.options("/api/papers/count", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert r.headers.get("access-control-allow-origin") != "*"
    assert "evil.example" not in (r.headers.get("access-control-allow-origin") or "")
