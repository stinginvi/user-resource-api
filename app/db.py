"""数据库连接池。

为什么要池：
- 建一条连接要 TCP 握手 + 身份认证，几十毫秒
- 每个请求都建一条，高并发时数据库连接数会爆掉
- 池子维护一组已经建好的连接：借一条、用完还回来、不重新登录
"""

import os

from dotenv import load_dotenv
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("缺少 DATABASE_URL，请检查项目根目录的 .env")

# open=False：导入时不连接，等应用启动再打开（lifespan 里做）
pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,      # 平时至少保持 1 条空闲连接
    max_size=10,     # 最多同时 10 条，超出的请求排队
    kwargs={"row_factory": dict_row},
    open=False,
)


def get_conn():
    """FastAPI 依赖：从池里借一条连接，请求结束后归还。"""
    with pool.connection() as conn:
        yield conn
