# user-resource-api

用 FastAPI + PostgreSQL + Redis 实现的「用户与笔记」REST 服务。P1 项目：完整的 CRUD、JWT 鉴权、资源权限、分页、缓存、全链路异步、统一错误响应和接口测试。

## 功能

- **注册 / 登录**：密码用 argon2 哈希存储，登录返回 JWT
- **用户**：查列表（limit）、查单个、改名、删除
- **笔记**：创建、分页列出、查单个、修改、删除
- **权限**：登录用户只能读写自己的笔记；删除用户时笔记级联删除
- **缓存**：用户详情走 Redis，cache-aside + 空值缓存 + 互斥锁 + 随机 TTL
- **异步**：async 路由 + AsyncSession（asyncpg）+ redis.asyncio
- **输入校验**：全部由 Pydantic 负责，错误返回统一结构
- **日志**：每个请求记录方法、路径、状态码、耗时

## 技术栈

| 组件 | 用途 |
|---|---|
| FastAPI | Web 框架、自动 OpenAPI 文档 |
| Pydantic v2 | 请求/响应校验 |
| SQLAlchemy 2.x（async） | ORM、连接池、事务 |
| asyncpg | PostgreSQL 异步驱动 |
| Alembic | 数据库迁移 |
| PostgreSQL 18 | 数据存储 |
| Redis | 缓存 |
| pwdlib + argon2 | 密码哈希 |
| PyJWT | 签发和校验 token |
| pytest + httpx | 接口测试 |

## 快速开始

### 1. 准备 PostgreSQL

```bash
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn"
psql -U postgres -h 127.0.0.1 -c "CREATE DATABASE learn_test"
```

### 2. 准备 Redis

Windows 版：

```bash
# 安装后作为服务运行，默认端口 6379
redis-cli ping
```

Docker：

```bash
docker run -d --name redis -p 6379:6379 redis:7-alpine
```

### 3. 安装依赖

```bash
python -m venv .venv
source .venv/Scripts/activate     # Windows Git Bash
pip install -r requirements.txt
```

### 4. 配置环境变量

在项目根目录创建 `.env`：

```
DATABASE_URL=postgresql://postgres:你的密码@127.0.0.1:5432/learn
SECRET_KEY=一段足够长的随机字符串
REDIS_URL=redis://127.0.0.1:6379/0
```

生成密钥：

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### 5. 建表

```bash
alembic upgrade head
```

### 6. 启动

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
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"password123"}'

curl -X POST http://127.0.0.1:8000/auth/login \
  -d "username=alice&password=password123"

curl http://127.0.0.1:8000/users/1/notes \
  -H "Authorization: Bearer <上一步拿到的 token>"
```

token 默认 **30 分钟**过期。

## 接口

| 方法 | 路径 | 鉴权 | 说明 | 成功 |
|---|---|---|---|---|
| GET | `/health` | 否 | 健康检查 | 200 |
| POST | `/auth/register` | 否 | 注册 | 201 |
| POST | `/auth/login` | 否 | 登录，返回 token | 200 |
| GET | `/users?limit=10` | 否 | 用户列表 | 200 |
| GET | `/users/{id}` | 否 | 查用户（走缓存） | 200 |
| PUT | `/users/{id}` | 否 | 修改用户名 | 200 |
| DELETE | `/users/{id}` | 否 | 删除用户（级联删笔记） | 204 |
| GET | `/users/{id}/notes?limit=10&offset=0` | 是 | 分页查自己的笔记 | 200 |
| POST | `/users/{id}/notes` | 是 | 给自己的笔记 | 201 |
| GET | `/notes/{id}` | 是 | 查自己的笔记 | 200 |
| PUT | `/notes/{id}` | 是 | 修改自己的笔记 | 200 |
| DELETE | `/notes/{id}` | 是 | 删除自己的笔记 | 204 |

## 缓存策略

`GET /users/{id}` 采用 **cache-aside**：

```
读：查缓存 → 命中返回 → 未命中查库 → 回填（TTL 300s ± 30s）
写：更新数据库 → 删除缓存
```

三种缓存问题的处理：

| 问题 | 解法 |
|---|---|
| 穿透（查不存在的数据） | 缓存 `__NULL__` 标记，TTL 60 秒 |
| 击穿（热点 key 过期） | `SET lock:<key> 1 NX EX 10` 互斥锁，只有一个请求回源 |
| 雪崩（大量 key 同时过期） | 过期时间加 ±30 秒随机抖动 |

## 异步

- 所有路由都是 `async def`
- 数据库：`AsyncSession` + asyncpg
- 缓存：`redis.asyncio`
- 依赖 `asyncio.gather` 并发聚合、`asyncio.wait_for` 超时控制

**注意**：`async def` 里不能调用同步阻塞函数（`time.sleep`、`requests`、同步数据库驱动），否则会卡住整个事件循环。

## 健康检查

| 端点 | 类型 | 检查内容 | 依赖故障时 |
|---|---|---|---|
| `GET /health` | liveness | 只确认进程活着 | 200 |
| `GET /health/ready` | readiness | PostgreSQL `SELECT 1` + Redis `PING` | **503**，并返回具体是哪个依赖 |

```bash
curl -s http://127.0.0.1:8000/health/ready
# {"status":"ok","checks":{"database":"ok","redis":"ok"}}
```

**为什么分开**：liveness 检查数据库会导致「数据库抖一下，容器被反复重启」；readiness 才负责决定要不要接流量。

## 压测

压测脚本：`locustfile.py`

```bash
locust -f locustfile.py --host http://127.0.0.1:8000 \
  --headless -u 50 -r 10 -t 30s --only-summary
```

本机实测（Windows、单进程 uvicorn、PostgreSQL 和 Redis 同机）：

| 并发 | QPS | 平均延迟 | P95 | P99 | 错误率 |
|---|---|---|---|---|---|
| 50 | 350 | 6 ms | 9 ms | 15 ms | 0% |
| 200 | 751 | 79 ms | 350 ms | 420 ms | 0% |

按接口拆开（200 并发）：

| 接口 | QPS | P95 | 说明 |
|---|---|---|---|
| `GET /users/{id}` | 529 | 74 ms | 走 Redis 缓存 |
| `GET /users?limit=10` | 146 | 430 ms | 每次查库 |
| `GET /health` | 76 | 53 ms | 不查库 |

**结论**：

- 缓存接口的 QPS 是查库接口的 3.6 倍，P95 低 5.8 倍
- 200 并发时列表接口开始排队，怀疑数据库连接池（最多 15 条）成为瓶颈
- 日志每请求写一行 stdout，Windows 终端 IO 会拖累事件循环（健康检查延迟也上涨）

**优化方向**：调大连接池、日志异步化、uvicorn 多 worker。

## Nginx 反向代理

```nginx
server {
    listen 80;
    server_name localhost;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # SSE 流式输出：关闭缓冲
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 300s;
    }
}
```

验证：`http://127.0.0.1/docs` 通过 80 端口能打开。

## CI

`.github/workflows/ci.yml`：

- 每次 push / PR 自动运行
- 起 PostgreSQL 18 和 Redis 7 作为 service 容器
- 安装依赖 → `alembic upgrade head` → `pytest -q`
- 使用测试专用密码，不碰真实配置

## Docker

`Dockerfile` 和 `.dockerignore` 已提供（多阶段分层、`.env` 不进镜像）：

```bash
docker build -t user-resource-api .
docker run -d --name api -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:密码@host.docker.internal:5432/learn" \
  -e SECRET_KEY="..." \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  user-resource-api
```

> 当前开发机未启用 WSL2（与 VMware 冲突），镜像构建未在本地验证。

### Docker Compose

`docker-compose.yml` 定义三个服务：`api`、`db`（PostgreSQL 18）、`redis`（Redis 7）。

```bash
docker compose up -d
docker compose exec api alembic upgrade head   # 首次启动后建表
```

要点：

- 容器之间用服务名互相访问（`db:5432`、`redis:6379`），不是 `localhost`
- `depends_on` 配合 `condition: service_healthy`，等数据库真正可用再启动 API
- 数据用 volume 持久化（`pgdata`、`redisdata`）
- 密码从宿主机的 `.env` 注入，不写进镜像

## 错误响应

```json
{"error": {"code": "USER_NOT_FOUND", "message": "用户不存在"}}
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

45 个测试，覆盖正常路径、401、403、404、409、422、分页、缓存行为和健康检查。

- 使用独立的 `learn_test` 库和 Redis 15 号库
- 每个用例开始前清表、清缓存

## 项目结构

```
user-resource-api/
├── app/
│   ├── main.py           # 组装：lifespan、中间件、异常、路由
│   ├── db.py             # AsyncEngine、AsyncSession、get_db
│   ├── models.py         # SQLAlchemy 模型
│   ├── schemas.py        # Pydantic 输入输出模型
│   ├── security.py       # 密码哈希、JWT、get_current_user
│   ├── cache.py          # Redis 异步客户端与缓存工具
│   ├── errors.py         # 统一错误响应
│   ├── logging_conf.py   # 日志格式
│   └── routers/
│       ├── auth.py
│       ├── users.py
│       └── notes.py
├── alembic/              # 迁移脚本
├── tests/
├── Dockerfile
├── init.sql              # 开发阶段快速重建
└── requirements.txt
```

## 已知限制

- 用户列表和改名接口还没加鉴权（只有笔记做了权限控制）
- 笔记列表没有缓存
- 没有刷新 token / 注销机制
- 分页用 offset，数据量很大时会变慢
- 日志同步写 stdout，高并发下会成为瓶颈
- Docker 镜像和 Compose 未在本机验证（WSL2 与 VMware 冲突）
- 尚未部署到云服务器，没有公网访问和线上压测数据
