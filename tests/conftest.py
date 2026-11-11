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

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import engine
from app.main import app


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def clean_db(client):
    """每个测试开始前清空表并重置自增 id，测试之间互不影响。"""
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE notes, users RESTART IDENTITY CASCADE"))
    yield
