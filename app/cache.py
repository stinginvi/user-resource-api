"""Redis 连接与缓存工具（异步版）。

Windows 版 Redis 是 3.0，必须用 RESP2（protocol=2）。
"""

import os
import random

import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
CACHE_TTL = 300
JITTER = 30


redis_client = redis.Redis.from_url(
    REDIS_URL,
    decode_responses=True,
    protocol=2,
)


async def cache_get(key: str) -> str | None:
    """读缓存；key 不存在返回 None。"""
    return await redis_client.get(key)


async def cache_set(key: str, value: str, ttl: int = CACHE_TTL) -> None:
    """写缓存。过期时间加随机抖动，防止雪崩。"""
    ttl_with_jitter = max(1, ttl + random.randint(-JITTER, JITTER))
    await redis_client.set(key, value, ex=ttl_with_jitter)


async def cache_delete(*keys: str) -> None:
    """删除缓存。写操作后调用。"""
    if keys:
        await redis_client.delete(*keys)


def user_key(user_id: int) -> str:
    """用户缓存的 key 规则：user:{id}"""
    return f"user:{user_id}"
