# VERSIONS.md — 版本历史

## v2.0.5 (2026-11-08)

### 安全修复
- **Critical** 移除 JWT 弱密钥风险：忽略 `change-this-*`/空值等占位密钥，改由环境变量注入强随机值；旧占位密钥签发的 token 已验证失效。
- **Critical** 业务文件下载增加登录与项目成员校验，未登录/非成员无法下载（原实测未登录可下载 file 5–8）。
- **Critical** 删除 `/debug/seed` 调试接口，停止泄露超管邮箱。
- **Critical** 移除硬编码初始密码（旧口令已废弃并完成轮换）；改为 `INITIAL_ADMIN_PASSWORD` 或随机生成并写入 0600 文件。
- **High** 任务、文件、统计、项目页面全部增加项目级授权，修复 IDOR。
- **High** 文件上传 `ebc_step` 仅接受固定步骤白名单，阻断路径穿越写入。
- **High** `/set-project` 增加登录与项目授权，并限制 `next` 仅可站内跳转（阻断开放重定向）。
- **High** 管理员角色调整仅超管可分配 admin/super_admin；禁止自我提权；系统至少保留一个超管。
- **High** 登录增加 IP+邮箱限流（5 次/15 分钟）；Cookie 增加 `Secure`；密码最小长度 8 位。
- **High** 上传增加 50MB 上限（请求头 + 流式计数双重校验）；异常不再回显 traceback。
- **High** 畸形 Cookie 不再触发 500；统一返回登录跳转。
- **Medium** 关闭 `/docs`、`/redoc`、`/openapi.json`；增加 CSP、HSTS、X-Frame-Options、nosniff、Referrer-Policy、Permissions-Policy。
- **Medium** 依赖升级：FastAPI 0.115.0→0.115.6、Starlette 0.38.6→0.41.3（修复 CVE-2024-47874 multipart DoS）、python-multipart 0.0.12→0.0.20。

### 配置与部署
- `docker-compose.yml` 移除重复端口映射与明文弱口令，改为从 NAS `/volume1/docker/ecs-pm/.env`（权限 600）注入 `POSTGRES_PASSWORD`/`SECRET_KEY`/`JWT_SECRET`。
- 生产 PostgreSQL `ecs` 用户密码已轮换；应用使用新镜像 `ecs-pm-app`，旧镜像保留回滚标签 `ecs-pm-app:pre-2.0.5`。
- 生效后所有既有登录会话失效（JWT 密钥轮换，预期行为）。

### 生产数据变更登记
- 本次**未修改任何业务数据**，仅轮换数据库账号密码。
- 改动前备份：`NAS 备份目录（ecs-pm-security-20261108-150944）`（源码、`ecs_pm.sql.gz`、`uploads.tar.gz`、Git bundle）。
- 核验方式：将备份恢复到临时库，与生产逐表比对 `md5(string_agg(row::text ORDER BY id))`；`users`/`projects`/`tasks`/`files`/`project_members` 五表全部 MATCH。
- 行数核对：3 users / 2 projects / 50 tasks / 4 files / 4 project_members，与备份一致。
- 上传卷核验：4 个文件与备份逐文件 MD5 完全一致；临时校验库与临时目录已删除。

### 验证
- 隔离环境（SQLite，FastAPI 0.115.6 + Starlette 0.41.3）：43 项安全/功能回归通过，覆盖登录、任务 CRUD、里程碑、上传/下载、越权 403、路径穿越、开放重定向、限流 429、超限 413、畸形 Cookie、安全头、调试接口 404。
- 真实 Chrome（隔离环境）：登录 → 仪表盘 → 甘特图 → 新增任务（中文正常）→ 文件库 → 用户管理，Console 0 错误。
- 生产自动化：`/docs` `/redoc` `/openapi.json` `/debug/seed` 均 404；未登录下载/任务接口 303；旧占位密钥伪造 token 被拒；6 项安全头经公网 nginx 透传生效；错误密码返回正常错误页（数据库连通）。
- 真实 Chrome（生产）：登录页正常渲染，Console 0 错误；登录后各页面待用户手动登录后复核。

### GitHub 说明
- `Samkkgz/ogd-gantt` 已含 MIT LICENSE（commit `1a4c036`），但仓库内容是静态 HTML + Supabase SQL，与当前 NAS FastAPI + PostgreSQL 版本**不是同一套代码**。
- 本仓库历史中含旧版弱口令，公开版本通过全新干净历史仓库发布，不复用旧历史。

## v2.0.4 (2026-11-04)

### 修复
- 新增/编辑行动计划：勾选“里程碑”后无法保存。甘特图表单的复选框提交值为 `1`，后端仅判断 `on`；现统一兼容 `1/on/true/yes`。

### 验证
- 本地真实 Chrome：新增勾选里程碑 → 任务行显示 ✦，统计 13→14，接口 `is_milestone=true`；编辑取消 → 统计回到 13，接口 `false`。
- 生产真实 Chrome（项目 8）：新增勾选里程碑 → 统计 0→1，任务行显示 ✦，接口 `is_milestone=true`；编辑取消 → 统计回到 0，接口 `false`。
- 验证任务（id 125）已删除，项目 8 恢复为 6 条任务、0 个里程碑，Console 0 错误。

## v2.0.3 (2026-11-04)

### 修复
- 登录页：登录失败时显示“邮箱或密码错误/账号未激活”提示，并回填已输入的邮箱，避免用户误以为提交无响应。
- 统计数据：修正 v2.0.2 之前新建任务被强制标记为草稿的问题，将已有真实任务恢复为正式任务。

### 生产数据变更登记
- 数据来源：生产库 `ecs_pm.tasks` 中 `is_draft=true` 且 `content` 或 `deliverable` 非空的记录。
- 影响范围：`tasks` 表 2 行（id 118「微信小程序开发」、id 119「test」，均属项目 8 Garden BC Tools）。
- 变更内容：`is_draft` 由 `true` 改为 `false`；项目 8 统计由 1 条恢复为 3 条。
- 备份路径：`/volume1/CodexBackup/ecs-pm-datapatch-20261104-105323/ecs_pm.sql`。
- 验证状态：生产页面统计显示「总任务 3 / 进行中 1 / 待开始 2」，与数据库一致。

### 验证
- 真实 Chrome 输入错误密码，页面显示错误提示且邮箱保留，Console 0 错误。
- 真实 Chrome 使用正确密码登录成功并跳转仪表盘。
- 生产环境错误密码提示正常显示。
- 生产真实 Chrome 通过「+ 新增」提交行动计划：`POST /api/projects/8/tasks/create` 返回 303，跳转 `/gantt?project_id=8` 返回 200，任务出现在列表，统计 3→4，Console 0 错误。
- 验证任务（id 121）已删除，统计恢复为 3，无测试数据残留。
- 生产真实 Chrome 点击导航「用户管理」：`/users` 正常渲染「用户管理 - Garden BC Tools」，3 行成员，Console 0 错误。
- 生产 `/admin?tab=users` 正常渲染，3 行用户，Console 0 错误。

## v2.0.2 (2026-11-04)

### 修复
- 新增行动计划：提交后的跳转由 307 改为 303，避免浏览器保留 POST 方法访问 `/gantt` 导致 `405 Method Not Allowed`。
- 新增行动计划：填写内容或产出后不再标记为草稿，创建后立即计入任务统计。
- 用户管理：将 `/users` 路由恢复到已跟踪的 `app/routes/projects.py`，移除对未跟踪的 `project_users.py` 及入口导入的依赖，避免生产环境文件版本不一致时 404。
- 用户管理：`project_id` Cookie 非法或项目已删除时安全跳回甘特图，不再返回 500。

### 验证
- 真实 Chrome 完成新增行动计划提交，页面 200，任务列表与统计同步更新，Console 0 错误。
- 真实 Chrome 访问 `/users` 与 `/admin?tab=users` 均正常渲染，Console 0 错误。

## v2.0.1 (2026-10-28)

### 公网静态资源与首屏优化
- `/static/*` 增加一年 immutable 缓存；HTML 使用 `private, no-cache, must-revalidate`。
- HTMX、Alpine、Lucide 和应用脚本改为 `defer`，并增加版本化查询参数。
- 服务端启用 GZip，降低 Tailscale/源站直连时静态脚本的传输体积。
- 本次只调整缓存与加载方式，不改变业务路由和数据逻辑。

### 验证
- Python 编译与补丁格式检查通过。
- NAS 已部署 `v2.0.1`；真实 Chrome 登录页 FCP 约 **0.16s**，静态资源缓存头正常，Console 0 错误、0 警告。

## v2.0.0 (2026-07-26)

### 重大变更
- **架构迁移**：Flask + Gunicorn + Nginx → FastAPI + Uvicorn
- **认证重写**：Flask-Login Session → JWT (httpOnly Cookie)
- **前端优化**：UI 对齐 Business Dashboard 风格

### 后端变动
- `app/database.py` — 新增：独立数据库引擎与会话管理
- `app/utils/auth.py` — 新增：JWT 认证工具（bcrypt, create_access_token, decode_access_token）
- `app/run.py` — 重写：FastAPI 应用入口（lifespan, AuthMiddleware, 模板渲染）
- `app/routes/*.py` — 全部重写：Flask Blueprint → FastAPI APIRouter
- `app/models/*.py` — 重写：从 db.Model → Base (declarative_base)
- `app/seed.py`, `app/seed_ogd.py` — 适配新的数据库模块

### 部署变动
- `Dockerfile` — CMD: gunicorn → uvicorn (端口 8765)
- `docker-compose.yml` — 移除 nginx 服务，app 端口映射 8081:8765
- `nginx/default.conf` — **已删除**（不再需要 Nginx 反向代理）
- `app/requirements.txt` — Flask 依赖 → FastAPI 依赖

### 之前版本
- v1.1.0 — Flask + Gunicorn + Nginx (最后备份版本)
