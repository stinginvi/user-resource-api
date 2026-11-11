"""鉴权与权限测试：401 / 403 / 本人可访问。"""

PASSWORD = "password123"


def _auth(client, username):
    client.post(
        "/auth/register", json={"username": username, "password": PASSWORD}
    )
    token = client.post(
        "/auth/login", data={"username": username, "password": PASSWORD}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_notes_require_token(client):
    r = client.get("/users/1/notes")
    assert r.status_code == 401


def test_invalid_token_rejected(client):
    r = client.get("/users/1/notes", headers={"Authorization": "Bearer not-a-token"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "INVALID_TOKEN"


def test_owner_can_access_own_note(client):
    alice = _auth(client, "alice")
    client.post("/users/1/notes", json={"title": "mine"}, headers=alice)

    r = client.get("/notes/1", headers=alice)
    assert r.status_code == 200


def test_other_user_cannot_access_note(client):
    alice = _auth(client, "alice")
    client.post("/users/1/notes", json={"title": "alice 的笔记"}, headers=alice)

    bob = _auth(client, "bob")  # bob 的 id 是 2

    assert client.get("/notes/1", headers=bob).status_code == 403
    assert client.get("/users/1/notes", headers=bob).status_code == 403
    assert client.put("/notes/1", json={"title": "hack"}, headers=bob).status_code == 403
    assert client.delete("/notes/1", headers=bob).status_code == 403

    # 确认原笔记没被改动
    r = client.get("/notes/1", headers=alice)
    assert r.status_code == 200
    assert r.json()["title"] == "alice 的笔记"
