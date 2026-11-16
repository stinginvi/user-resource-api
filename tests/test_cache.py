"""缓存行为测试：命中、失效、空值缓存、TTL。"""

import os

import redis

# 同步客户端只用于检查缓存状态，和 conftest 里清库用的是同一个 15 号库
_sync_redis = redis.Redis.from_url(
    os.environ["REDIS_URL"], decode_responses=True, protocol=2
)

PASSWORD = "password123"


def _register(client, username="alice"):
    return client.post(
        "/auth/register", json={"username": username, "password": PASSWORD}
    )


def test_user_is_cached_after_read(client):
    _register(client)
    client.get("/users/1")
    assert _sync_redis.get("user:1") is not None


def test_second_read_still_works(client):
    _register(client)
    first = client.get("/users/1")
    second = client.get("/users/1")
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()


def test_update_invalidates_cache(client):
    _register(client)
    client.get("/users/1")
    assert _sync_redis.get("user:1") is not None

    client.put("/users/1", json={"username": "alice2"})
    assert _sync_redis.get("user:1") is None

    # 再读一次，缓存重新回填
    client.get("/users/1")
    assert _sync_redis.get("user:1") is not None


def test_delete_invalidates_cache(client):
    _register(client)
    client.get("/users/1")
    client.delete("/users/1")
    assert _sync_redis.get("user:1") is None


def test_missing_user_is_cached_as_null(client):
    _register(client)

    first = client.get("/users/999")
    assert first.status_code == 404
    # 防穿透：不存在的用户也缓存
    assert _sync_redis.get("user:999") == "__NULL__"

    second = client.get("/users/999")
    assert second.status_code == 404


def test_cache_has_ttl_with_jitter(client):
    _register(client)
    client.get("/users/1")
    ttl = _sync_redis.ttl("user:1")
    # 默认 300 秒，随机抖动 ±30
    assert 0 < ttl <= 330
