"""pytest 公共配置。

测试连接串从 .env 的 DATABASE_URL 派生：只把库名换成 learn_test。
这样仓库里不会出现任何密码。

必须在导入 app 之前设置环境变量，否则 db.py 会连上开发库。
"""

import os
from urllib.parse import urlsplit, urlunsplit

from dotenv import load_dotenv

load_dotenv()

_base = os.environ.get("DATABASE_URL")
if not _base:
    raise RuntimeError("缺少 DATABASE_URL：请先在项目根目录创建 .env")

_parts = urlsplit(_base)
os.environ["DATABASE_URL"] = urlunsplit(_parts._replace(path="/learn_test"))

# 测试用 15 号库，和开发用的 0 号库隔离
os.environ["REDIS_URL"] = "redis://127.0.0.1:6379/15"

import psycopg
import pytest
import redis
from fastapi.testclient import TestClient

from app.main import app

TEST_DB_URL = os.environ["DATABASE_URL"]

# 同步客户端只在 fixture 里用于清库，避免和异步引擎跨事件循环
_sync_redis = redis.Redis.from_url(
    os.environ["REDIS_URL"], decode_responses=True, protocol=2
)


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    """每个测试开始前清空数据库和 Redis，测试之间互不影响。"""
    with psycopg.connect(TEST_DB_URL) as conn:
        conn.execute("TRUNCATE notes, users RESTART IDENTITY CASCADE")
        conn.commit()
    _sync_redis.flushdb()
    yield
