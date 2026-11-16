"""健康检查测试：liveness、readiness、依赖故障。"""

from app import cache
from app.db import get_db
from app.main import app


def test_liveness_always_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_ready_when_all_dependencies_ok(client):
    r = client.get("/health/ready")
    assert r.status_code == 200
    assert r.json()["checks"] == {"database": "ok", "redis": "ok"}


def test_ready_returns_503_when_redis_down(client, monkeypatch):
    async def broken_ping():
        raise ConnectionError("redis down")

    monkeypatch.setattr(cache.redis_client, "ping", broken_ping)

    r = client.get("/health/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["error"]["code"] == "NOT_READY"
    assert "redis" in body["error"]["message"]


def test_ready_returns_503_when_database_down(client):
    class BrokenSession:
        async def execute(self, *args, **kwargs):
            raise ConnectionError("database down")

    async def broken_db():
        yield BrokenSession()

    app.dependency_overrides[get_db] = broken_db
    try:
        r = client.get("/health/ready")
        assert r.status_code == 503
        body = r.json()
        assert body["error"]["code"] == "NOT_READY"
        assert "database" in body["error"]["message"]
    finally:
        app.dependency_overrides.clear()
