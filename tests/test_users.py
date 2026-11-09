"""用户接口测试。

每条测试都从空库开始（clean_db 负责），所以 id 一定能预测。
"""


def test_create_user(client):
    r = client.post("/users", json={"username": "alice"})
    assert r.status_code == 201
    body = r.json()
    assert body["id"] == 1
    assert body["username"] == "alice"
    assert "created_at" in body


def test_create_duplicate_username(client):
    client.post("/users", json={"username": "alice"})
    r = client.post("/users", json={"username": "alice"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "USERNAME_CONFLICT"


def test_create_short_username(client):
    r = client.post("/users", json={"username": "ab"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"
    assert r.json()["error"]["details"][0]["field"] == "body.username"


def test_list_users_with_limit(client):
    for name in ("alice", "bob", "carol"):
        client.post("/users", json={"username": name})

    r = client.get("/users?limit=2")
    assert r.status_code == 200
    assert [u["username"] for u in r.json()] == ["alice", "bob"]


def test_get_user(client):
    client.post("/users", json={"username": "alice"})
    r = client.get("/users/1")
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_get_user_not_found(client):
    r = client.get("/users/999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "USER_NOT_FOUND"


def test_update_user(client):
    client.post("/users", json={"username": "alice"})
    r = client.put("/users/1", json={"username": "alice2"})
    assert r.status_code == 200
    assert r.json()["username"] == "alice2"


def test_update_duplicate_username(client):
    client.post("/users", json={"username": "alice"})
    client.post("/users", json={"username": "bob"})
    r = client.put("/users/2", json={"username": "alice"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "USERNAME_CONFLICT"


def test_update_empty_body(client):
    client.post("/users", json={"username": "alice"})
    r = client.put("/users/1", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NO_FIELDS_TO_UPDATE"


def test_delete_user(client):
    client.post("/users", json={"username": "alice"})
    assert client.delete("/users/1").status_code == 204
    assert client.get("/users/1").status_code == 404
