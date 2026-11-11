# user-resource-api

用 FastAPI + PostgreSQL 实现的「用户与笔记」REST 服务。P1 项目：完整的 CRUD、JWT 鉴权、资源权限、分页、统一错误响应和接口测试。

## 功能

- **注册 / 登录**：密码用 argon2 哈希存储，登录返回 JWT
- **用户**：查列表（limit）、查单个、改名、删除
- **笔记**：创建、分页列出、查单个、修改、删除
- **权限**：登录用户只能读写自己的笔记；删除用户时笔记级联删除
- **输入校验**：全部由 Pydantic 负责，错误返回统一结构
- **日志**：每个请求记录方法、路径、状态码、耗时

## 技术栈

| 组件 | 用途 |
|---|---|
| FastAPI | Web 框架、自动 OpenAPI 文档 |
| Pydantic v2 | 请求/响应校验 |
| SQLAlchemy 2.x | ORM、连接池、事务 |
| Alembic | 数据库迁移 |
| PostgreSQL 18 | 数据存储 |
| pwdlib + argon2 | 密码哈希 |
| PyJWT | 签发和校验 token |
| pytest + httpx | 接口测试 |

## 快速开始

### 1. 准备数据库

```bash
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn"
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn_test"
```

### 2. 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
pip install -r requirements.txt
```

### 3. 配置环境变量

在项目根目录创建 `.env`：

```
DATABASE_URL=postgresql://postgres:你的密码@127.0.0.1:5432/learn
SECRET_KEY=随便生成一段足够长的随机字符串
```

生成密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 4. 建表（用迁移）

```bash
alembic upgrade head
alembic -x db=test upgrade head    # 如需要，测试库用同一套迁移
```

> 开发阶段想彻底重建，也可以执行 `psql -U postgres -h 127.0.0.1 -d learn -f init.sql`，但**有真实数据后不要这么做**。

### 5. 启动

```bash
uvicorn app.main:app --reload
```

- 服务：http://127.0.0.1:8000
- 交互文档：http://127.0.0.1:8000/docs
- 在 `/docs` 右上角 **Authorize** 里输入用户名密码即可自动带 token

## 鉴权流程

```
1. POST /auth/register   注册（用户名 + 密码）
2. POST /auth/login      登录（表单），拿到 access_token
3. 后续请求带 Authorization: Bearer <access_token>
```

```bash
# 注册
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'

# 登录（注意是表单，不是 JSON）
curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=alice&password=password123"

# 用 token 访问
curl http://127.0.0.1:8000/users/1/notes \
  -H "Authorization: Bearer <上一步拿到的 token>"
```

token 默认 **30 分钟**过期（`app/security.py` 的 `ACCESS_TOKEN_EXPIRE_MINUTES`）。

## 接口

| 方法 | 路径 | 鉴权 | 说明 | 成功 |
|---|---|---|---|---|
| GET | `/health` | 否 | 健康检查 | 200 |
| POST | `/auth/register` | 否 | 注册 | 201 |
| POST | `/auth/login` | 否 | 登录，返回 token | 200 |
| GET | `/users?limit=10` | 否 | 用户列表 | 200 |
| GET | `/users/{id}` | 否 | 查用户 | 200 |
| PUT | `/users/{id}` | 否 | 修改用户名 | 200 |
| DELETE | `/users/{id}` | 否 | 删除用户（级联删笔记） | 204 |
| GET | `/users/{id}/notes?limit=10&offset=0` | **是** | 分页查自己的笔记 | 200 |
| POST | `/users/{id}/notes` | **是** | 给自己的笔记 | 201 |
| GET | `/notes/{id}` | **是** | 查自己的笔记 | 200 |
| PUT | `/notes/{id}` | **是** | 修改自己的笔记 | 200 |
| DELETE | `/notes/{id}` | **是** | 删除自己的笔记 | 204 |

### 分页返回

```json
{
  "items": [{"id": 1, "title": "...", "...": "..."}],
  "total": 37,
  "limit": 10,
  "offset": 0
}
```

`limit` 上限 100，`offset` 从 0 开始。

## 错误响应

所有错误统一为：

```json
{"error": {"code": "USER_NOT_FOUND", "message": "用户不存在"}}
```

参数校验失败时多一个 `details`：

```json
{"error": {"code": "VALIDATION_ERROR", "message": "参数校验失败",
           "details": [{"field": "body.username", "message": "..."}]}}
```

| code | 状态码 | 含义 |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 登录用户名或密码错误 |
| `INVALID_TOKEN` | 401 | token 无效或已过期 |
| `HTTP_ERROR` | 401 | 未携带 token |
| `FORBIDDEN` | 403 | 无权访问该资源 |
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

- 使用独立的 `learn_test` 库，每个用例开始前清表
- 覆盖正常路径、401、403、404、409、422 和分页

## 项目结构

```
user-resource-api/
├── app/
│   ├── main.py           # 组装：lifespan、中间件、异常、路由
│   ├── db.py             # Engine、Session、get_db
│   ├── models.py         # SQLAlchemy 模型
│   ├── schemas.py        # Pydantic 输入输出模型
│   ├── security.py       # 密码哈希、JWT、get_current_user
│   ├── errors.py         # 统一错误响应
│   ├── logging_conf.py   # 日志格式
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       └── notes.py
├── alembic/              # 迁移脚本（要进 Git）
├── tests/
├── init.sql              # 开发阶段快速重建
└── requirements.txt
```

## 已知限制

- 用户列表和改名接口还没加鉴权（只有笔记做了权限控制）
- 没有刷新 token / 注销机制
- 分页用 offset，数据量很大时会变慢
- 没有缓存（W6）
- 只在本地运行，未部署（W7）
