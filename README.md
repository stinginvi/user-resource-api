# user-resource-api

用 FastAPI + PostgreSQL 实现的「用户与笔记」REST 服务。P1 骨架项目：包含完整的 CRUD、参数校验、统一错误响应、请求日志和接口测试。

## 功能

- 用户：创建、列表（limit）、查单个、改名、删除
- 笔记：给用户创建、按用户列出、查单个、修改、删除；删除用户时笔记级联删除
- 所有输入由 Pydantic 校验，错误返回统一格式
- 每个请求记录方法、路径、状态码、耗时

## 技术栈

| 组件 | 用途 |
|---|---|
| FastAPI | Web 框架、自动 OpenAPI 文档 |
| Pydantic v2 | 请求/响应校验 |
| psycopg 3 + psycopg_pool | PostgreSQL 驱动与连接池 |
| PostgreSQL 18 | 数据存储 |
| pytest + httpx | 接口测试 |

## 快速开始

### 1. 准备数据库

需要本机 PostgreSQL（默认端口 5432）。建库：

```bash
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn"
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn_test"
```

### 2. 建表

```bash
psql -U postgres -h 127.0.0.1 -d learn -f init.sql
psql -U postgres -h 127.0.0.1 -d learn_test -f init.sql
```

> `init.sql` 会先 `DROP TABLE` 再建，适合开发阶段重置；**上线后不要重复执行**。

### 3. 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
pip install -r requirements.txt
```

### 4. 配置连接串

在项目根目录创建 `.env`：

```
DATABASE_URL=postgresql://postgres:你的密码@127.0.0.1:5432/learn
```

### 5. 启动

```bash
uvicorn app.main:app --reload
```

- 服务：http://127.0.0.1:8000
- 交互文档：http://127.0.0.1:8000/docs

## 接口

| 方法 | 路径 | 说明 | 成功 |
|---|---|---|---|
| GET | `/health` | 健康检查 | 200 |
| GET | `/users?limit=10` | 用户列表 | 200 |
| POST | `/users` | 创建用户 | 201 |
| GET | `/users/{id}` | 查用户 | 200 |
| PUT | `/users/{id}` | 修改用户名 | 200 |
| DELETE | `/users/{id}` | 删除用户（级联删笔记） | 204 |
| GET | `/users/{id}/notes` | 某用户的笔记 | 200 |
| POST | `/users/{id}/notes` | 给用户建笔记 | 201 |
| GET | `/notes/{id}` | 查笔记 | 200 |
| PUT | `/notes/{id}` | 修改笔记 | 200 |
| DELETE | `/notes/{id}` | 删除笔记 | 204 |

### 示例

```bash
# 创建用户
curl -X POST http://127.0.0.1:8000/users \
  -H "Content-Type: application/json" \
  -d '{"username":"alice"}'

# 给用户建笔记
curl -X POST http://127.0.0.1:8000/users/1/notes \
  -H "Content-Type: application/json" \
  -d '{"title":"第一篇","content":"hello"}'

# 查用户的笔记
curl http://127.0.0.1:8000/users/1/notes
```

## 错误响应

所有错误统一为：

```json
{
  "error": {
    "code": "USER_NOT_FOUND",
    "message": "用户不存在"
  }
}
```

参数校验失败时多一个 `details`：

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数校验失败",
    "details": [
      {"field": "body.username", "message": "String should have at least 3 characters"}
    ]
  }
}
```

| code | 状态码 | 含义 |
|---|---|---|
| `USER_NOT_FOUND` | 404 | 用户不存在 |
| `NOTE_NOT_FOUND` | 404 | 笔记不存在 |
| `USERNAME_CONFLICT` | 409 | 用户名重复 |
| `VALIDATION_ERROR` | 422 | 参数格式不对 |
| `NO_FIELDS_TO_UPDATE` | 422 | PUT 没有可修改的字段 |
| `INTERNAL_ERROR` | 500 | 服务端未预料错误（详情只进日志） |

## 测试

```bash
pytest -q
```

测试使用独立的 `learn_test` 库，每个用例开始前清表，不会碰开发库。

## 项目结构

```
user-resource-api/
├── app/
│   ├── main.py           # 组装：lifespan、中间件、异常、路由
│   ├── db.py             # 连接池与 get_conn 依赖
│   ├── schemas.py        # Pydantic 输入输出模型
│   ├── errors.py         # 统一错误响应
│   ├── logging_conf.py   # 日志格式
│   └── routers/
│       ├── users.py
│       └── notes.py
├── tests/
│   ├── conftest.py
│   ├── test_users.py
│   └── test_notes.py
├── init.sql
├── requirements.txt
└── .env                  # 不提交
```

## 已知限制

- 没有鉴权：任何人都能读写所有用户和笔记（W5 加 JWT）
- 用户列表只有 `limit`，没有 `offset` 分页
- 没有缓存（W6）
- 只在本地运行，未部署（W7）
