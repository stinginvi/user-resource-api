"""笔记接口测试。"""


def _create_user(client, username="alice"):
    return client.post("/users", json={"username": username}).json()


def test_create_note(client):
    _create_user(client)
    r = client.post("/users/1/notes", json={"title": "first", "content": "hello"})
    assert r.status_code == 201
    body = r.json()
    assert body["user_id"] == 1
    assert body["title"] == "first"
    assert body["content"] == "hello"


def test_create_note_content_defaults_to_empty(client):
    _create_user(client)
    r = client.post("/users/1/notes", json={"title": "only title"})
    assert r.status_code == 201
    assert r.json()["content"] == ""


def test_create_note_for_missing_user(client):
    r = client.post("/users/999/notes", json={"title": "ghost"})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "USER_NOT_FOUND"


def test_create_note_empty_title(client):
    _create_user(client)
    r = client.post("/users/1/notes", json={"title": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "VALIDATION_ERROR"


def test_list_notes(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "a"})
    client.post("/users/1/notes", json={"title": "b"})

    r = client.get("/users/1/notes")
    assert r.status_code == 200
    assert [n["title"] for n in r.json()] == ["a", "b"]


def test_list_notes_missing_user(client):
    r = client.get("/users/999/notes")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "USER_NOT_FOUND"


def test_get_note(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "first"})
    r = client.get("/notes/1")
    assert r.status_code == 200
    assert r.json()["title"] == "first"


def test_get_note_not_found(client):
    r = client.get("/notes/999")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOTE_NOT_FOUND"


def test_update_note(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "old", "content": "keep me"})

    r = client.put("/notes/1", json={"title": "new"})
    assert r.status_code == 200
    assert r.json()["title"] == "new"
    assert r.json()["content"] == "keep me"


def test_update_note_empty_body(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "x"})
    r = client.put("/notes/1", json={})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "NO_FIELDS_TO_UPDATE"


def test_delete_note(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "x"})
    assert client.delete("/notes/1").status_code == 204
    assert client.get("/notes/1").status_code == 404


def test_delete_user_cascades_notes(client):
    _create_user(client)
    client.post("/users/1/notes", json={"title": "x"})

    assert client.delete("/users/1").status_code == 204
    assert client.get("/notes/1").status_code == 404
