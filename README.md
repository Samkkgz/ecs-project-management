# ECS 项目管理系统

多公司协作的项目甘特图与交付物管理系统。后端 FastAPI + PostgreSQL，前端为服务端渲染的单页工作台，支持 Docker 单机部署。

## 功能

- 多项目切换与项目级成员权限
- EBC 步骤 / 阶段 / 状态三维筛选的甘特图
- 任务新增、编辑、删除、拖拽改期、里程碑标记
- 项目文件库：按 EBC 步骤归档、上传、下载、删除
- 用户与角色管理（`user` / `admin` / `super_admin`）
- 登录限流、会话 Cookie、审计友好的错误处理

## 技术栈

| 组件 | 版本 |
|---|---|
| Python | 3.12 |
| FastAPI | 0.115.6 |
| Starlette | 0.41.3 |
| SQLAlchemy | 2.0.36 |
| PostgreSQL | 16 |
| Jinja2 + HTMX + Alpine.js + Frappe Gantt | 服务端渲染前端 |

## 快速开始

```bash
cp .env.example .env
# 生成三个独立强密钥并填入 .env
openssl rand -base64 48   # POSTGRES_PASSWORD
openssl rand -base64 48   # SECRET_KEY
openssl rand -base64 48   # JWT_SECRET

docker compose up -d --build
```

首次启动且数据库无用户时，系统会生成随机超级管理员密码并写入容器内
`/data/initial_admin_password.txt`：

```bash
docker exec ecs-pm-app cat /data/initial_admin_password.txt
```

也可以显式指定初始管理员：

```bash
INITIAL_ADMIN_PASSWORD='<strong-password>' INITIAL_ADMIN_EMAIL='admin@example.com' docker compose up -d
```

## 环境变量

| 变量 | 必填 | 说明 |
|---|---|---|
| `POSTGRES_PASSWORD` | 是 | 数据库 `ecs` 用户密码 |
| `SECRET_KEY` | 是 | 应用密钥，至少 32 字符 |
| `JWT_SECRET` | 是 | JWT 签名密钥，至少 32 字符；轮换后所有会话失效 |
| `DATABASE_URL` | 否 | 默认由 `POSTGRES_PASSWORD` 组合生成 |
| `UPLOAD_FOLDER` | 否 | 默认 `/data/files` |
| `MAX_CONTENT_LENGTH` | 否 | 单文件上限，默认 52428800（50MB） |
| `COOKIE_SECURE` | 否 | 默认 `true`，请始终通过 HTTPS 访问 |
| `LOGIN_MAX_ATTEMPTS` | 否 | 默认 5 次 / `LOGIN_WINDOW_SECONDS`（900 秒） |

## 本地开发

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt

export SECRET_KEY="$(openssl rand -base64 48)"
export JWT_SECRET="$(openssl rand -base64 48)"
export DATABASE_URL="sqlite:///$(pwd)/data/dev.db"
export UPLOAD_FOLDER="$(pwd)/data/files"
export COOKIE_SECURE=false

cd app && uvicorn run:app --reload --port 8081
```

## 安全设计

v2.0.5 起默认启用：

- 占位/弱 JWT 密钥会被忽略，必须由环境变量注入强随机值
- 任务、文件、统计、项目页面均校验项目成员关系
- 文件上传扩展名白名单、EBC 步骤白名单、50MB 流式上限
- 登录按 IP + 邮箱限流，Cookie 默认 `Secure` / `HttpOnly` / `SameSite=Lax`
- 关闭 `/docs`、`/redoc`、`/openapi.json`，移除调试接口
- 统一安全响应头：CSP、HSTS、X-Frame-Options、nosniff、Referrer-Policy 等
- Starlette 0.41.3 修复 CVE-2024-47874

安全策略与漏洞报告方式见 [SECURITY.md](SECURITY.md)。

## 版本

当前版本 **v2.0.5**，变更记录见 [VERSIONS.md](VERSIONS.md)。

## 许可证

[MIT](LICENSE)
