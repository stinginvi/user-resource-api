"""注册、登录与密码存储测试。"""

from sqlalchemy import select

from app.db import SessionLocal
from app.models import User
from app.security import decode_access_token

PASSWORD = "password123"


def _register(client, username="alice", password=PASSWORD):
    return client.post(
        "/auth/register", json={"username": username, "password": password}
    )


def test_register_success(client):
    r = _register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["username"] == "alice"
    assert "password" not in body
    assert "password_hash" not in body


def test_register_password_too_short(client):
    r = _register(client, password="short")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    fields = [d["field"] for d in r.json()["error"]["details"]]
    assert "body.password" in fields


def test_register_duplicate(client):
    _register(client)
    r = _register(client)
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "USERNAME_CONFLICT"


def test_password_is_stored_hashed(client):
    _register(client)
    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.username == "alice"))
        assert user.password_hash != PASSWORD
        assert user.password_hash.startswith("$argon2")
    finally:
        db.close()


def test_login_success(client):
    _register(client)
    r = client.post("/auth/login", data={"username": "alice", "password": PASSWORD})
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_login_wrong_password(client):
    _register(client)
    r = client.post(
        "/auth/login", data={"username": "alice", "password": "wrongpass"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_unknown_user(client):
    r = client.post(
        "/auth/login", data={"username": "nobody", "password": PASSWORD}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_token_contains_user_id(client):
    _register(client)
    token = client.post(
        "/auth/login", data={"username": "alice", "password": PASSWORD}
    ).json()["access_token"]
    assert decode_access_token(token) == 1
