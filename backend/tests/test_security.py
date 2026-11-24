import time

import jwt
import pytest
from fastapi import FastAPI, Header
from fastapi.testclient import TestClient

from app import security

security._secret = "x" * 32

app = FastAPI()
app.add_middleware(security.AuthMiddleware)


@app.get("/folders")
def folders(x_user_id: str | None = Header(None)):
    return {"uid": x_user_id}


@app.get("/papers")
def papers(x_user_id: str | None = Header(None)):
    return {"uid": x_user_id}


@app.post("/user/guest")
def guest():
    return {"ok": True}


client = TestClient(app)


def bearer(uid="u1", **kw):
    return {"Authorization": f"Bearer {security.create_access_token(uid, **kw)}"}


def test_protected_requires_token():
    assert client.get("/folders").status_code == 401


def test_spoofed_header_alone_rejected():
    assert client.get("/folders", headers={"X-User-ID": "victim"}).status_code == 401


def test_spoofed_header_overridden_by_token():
    r = client.get("/folders", headers={**bearer("alice"), "X-User-ID": "victim"})
    assert r.status_code == 200 and r.json() == {"uid": "alice"}


def test_public_path_strips_spoofed_header():
    r = client.get("/papers", headers={"X-User-ID": "victim"})
    assert r.status_code == 200 and r.json() == {"uid": None}


def test_public_path_with_token_gets_verified_id():
    assert client.get("/papers", headers=bearer("bob")).json() == {"uid": "bob"}


def test_guest_endpoint_public():
    assert client.post("/user/guest").status_code == 200


def test_expired_token_rejected():
    tok = jwt.encode({"sub": "u", "exp": int(time.time()) - 10}, "x" * 32, algorithm="HS256")
    assert client.get("/folders", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_wrong_signature_rejected():
    tok = jwt.encode({"sub": "u", "exp": int(time.time()) + 100}, "y" * 32, algorithm="HS256")
    assert client.get("/folders", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_alg_none_rejected():
    tok = jwt.encode({"sub": "u", "exp": int(time.time()) + 100}, None, algorithm="none")
    assert client.get("/folders", headers={"Authorization": f"Bearer {tok}"}).status_code == 401


def test_garbage_token_rejected():
    assert client.get("/folders", headers={"Authorization": "Bearer nope"}).status_code == 401


def test_search_with_trailing_slash_is_public():
    from fastapi import FastAPI
    a = FastAPI()
    a.add_middleware(security.AuthMiddleware)

    @a.post("/search/")
    def s():
        return {"ok": True}

    @a.post("/searchevil")
    def e():
        return {"ok": True}

    c = TestClient(a)
    assert c.post("/search/").status_code == 200
    assert c.post("/searchevil").status_code == 401   # prefix match is path-segment aware
