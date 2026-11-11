"""笔记接口测试。

每个测试先注册并登录，请求带 Authorization 头。
"""

PASSWORD = "password123"


def _register(client, username="alice"):
    client.post(
        "/auth/register", json={"username": username, "password": PASSWORD}
    )


def _login(client, username="alice"):
    token = client.post(
        "/auth/login", data={"username": username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _auth(client, username="alice"):
    _register(client, username)
    return _login(client, username)


def test_create_note(client):
    headers = _auth(client)
    r = client.post(
        "/users/1/notes",
        json={"title": "first", "content": "hello"},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == 1
    assert body["title"] == "first"
    assert body["content"] == "hello"


def test_create_note_content_defaults_to_empty(client):
    headers = _auth(client)
    r = client.post(
        "/users/1/notes", json={"title": "only title"}, headers=headers
    )
    assert r.status_code == 201
    assert r.json()["content"] == ""


def test_create_note_for_other_user_is_forbidden(client):
    """先判权限，所以给「别人」建笔记是 403，而不是 404。"""
    headers = _auth(client)
    r = client.post(
        "/users/999/notes", json={"title": "ghost"}, headers=headers
    )
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "FORBIDDEN"


def test_create_note_empty_title(client):
    headers = _auth(client)
    r = client.post("/users/1/notes", json={"title": ""}, headers=headers)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_notes(client):
    headers = _auth(client)
    client.post("/users/1/notes", json={"title": "a"}, headers=headers)
    client.post("/users/1/notes", json={"title": "b"}, headers=headers)

    r = client.get("/users/1/notes", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert [n["title"] for n in body["items"]] == ["a", "b"]
    assert body["total"] == 2
    assert body["limit"] == 10
    assert body["offset"] == 0


def test_list_notes_pagination(client):
    headers = _auth(client)
    for title in ("a", "b", "c"):
        client.post("/users/1/notes", json={"title": title}, headers=headers)

    r = client.get("/users/1/notes?limit=2&offset=1", headers=headers)
    body = r.json()
    assert body["total"] == 3
    assert body["limit"] == 2
    assert body["offset"] == 1
    assert [n["title"] for n in body["items"]] == ["b", "c"]


def test_list_notes_of_other_user_is_forbidden(client):
    headers = _auth(client)
    r = client.get("/users/999/notes", headers=headers)
    assert r.status_code == 403


def test_get_note(client):
    headers = _auth(client)
    client.post("/users/1/notes", json={"title": "first"}, headers=headers)
    r = client.get("/notes/1", headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "first"


def test_get_note_not_found(client):
    headers = _auth(client)
    r = client.get("/notes/999", headers=headers)
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOTE_NOT_FOUND"


def test_update_note(client):
    headers = _auth(client)
    client.post(
        "/users/1/notes", json={"title": "old", "content": "keep me"}, headers=headers
    )

    r = client.put("/notes/1", json={"title": "new"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "new"
    assert r.json()["content"] == "keep me"


def test_update_note_empty_body(client):
    headers = _auth(client)
    client.post("/users/1/notes", json={"title": "x"}, headers=headers)
    r = client.put("/notes/1", json={}, headers=headers)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NO_FIELDS_TO_UPDATE"


def test_delete_note(client):
    headers = _auth(client)
    client.post("/users/1/notes", json={"title": "x"}, headers=headers)
    assert client.delete("/notes/1", headers=headers).status_code == 204
    assert client.get("/notes/1", headers=headers).status_code == 404


def test_delete_user_cascades_notes(client):
    from sqlalchemy import select

    from app.db import SessionLocal
    from app.models import Note

    headers = _auth(client)
    client.post("/users/1/notes", json={"title": "x"}, headers=headers)

    assert client.delete("/users/1").status_code == 204

    # 用户没了，他手里的 token 立刻失效
    assert client.get("/notes/1", headers=headers).status_code == 401

    # 笔记确实被外键级联删除了
    db = SessionLocal()
    try:
        assert db.scalar(select(Note).where(Note.id == 1)) is None
    finally:
        db.close()
