# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概况

这是一个面向高校机房课堂教学场景的 B/S 架构教学辅助系统。后端运行于教师机，学生通过局域网内浏览器访问。系统支持学生导入、签到、公告、问答、作业、AI 辅助反馈、学习效果评估和备份恢复等功能。

**核心部署约束**：
- 程序和配置可放在 U 盘
- 数据库必须位于教师机本地磁盘（默认 `C:\TeachingAssist\data\teaching_assist.db`）
- SQLite 使用 WAL 模式和 `synchronous=NORMAL`
- 支持无外网或 AI 不可用时的基础功能降级

## 技术栈

- **后端**：Python + FastAPI + Uvicorn + SQLite
- **前端**：React + Vite + TypeScript + MUI + Zustand
- **实时通信**：WebSocket（课堂公告、问题发布、答题状态推送）
- **环境约束**：Node 16.19.1（前端依赖固定为兼容版本，不要升级到需要 Node 18+ 的依赖）

## 常用命令

### 后端开发

初始化（首次）：
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Resolve-Path .).Path
cd ..
python scripts\init_db.py
```

启动后端：
```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
cd backend
python run.py
```

直接指定端口：
```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

验证后端语法：
```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
```

### 前端开发

开发模式：
```powershell
cd frontend
npm install
npm run dev
```

构建验证：
```powershell
cd frontend
npm run build
```

### 健康检查

```powershell
curl.exe http://127.0.0.1:8080/api/v1/health
curl.exe http://127.0.0.1:8080/api/v1/system/startup
```

### 打包部署

Windows 可执行程序打包：
```powershell
.\scripts\build_release.ps1
```

生成 U 盘部署包：
```powershell
.\scripts\make_usb_package.ps1
```

## 架构要点

### 数据库迁移机制

- 迁移文件位于 [backend/app/db/migrations/](backend/app/db/migrations/)，按版本号命名（如 `001_initial.sql`）
- 通过 [backend/app/db/migrations.py](backend/app/db/migrations.py) 的 `run_migrations()` 自动执行
- 迁移历史记录在 `schema_migrations` 表中
- **重要**：数据库结构变更必须通过新增迁移文件实现，不得直接修改已应用的迁移

### 端口备选机制

[backend/run.py](backend/run.py) 实现了端口备选逻辑：
- 默认尝试 8080
- 如被占用，依次尝试 8081、8888
- 配置位于 [config/default.yaml](config/default.yaml) 的 `server.fallback_ports`

### 统一响应格式

所有 API 返回统一的 `ApiResponse` 结构（定义在 [backend/app/schemas/response.py](backend/app/schemas/response.py)）：
```python
{
  "success": bool,
  "code": str,
  "message": str,
  "data": Any
}
```

使用 `ok()` 和 `fail()` 辅助函数构造响应。

### 异常处理

- 业务错误使用 `AppError`（定义在 [backend/app/core/exceptions.py](backend/app/core/exceptions.py)）
- 全局异常处理器会自动转换为统一响应格式
- 不要在代码中手动构造 400/500 响应，应抛出 `AppError`

### 鉴权机制

- 教师端使用 Bearer Token 鉴权（依赖注入：`app.api.deps.require_teacher_token`）
- 学生端通过学号和姓名双因子验证（不需要预注册）
- 初次启动需要教师设置密码（`POST /api/v1/auth/setup`）

### WebSocket 实时推送

- WebSocket 路由定义在 [backend/app/api/routes/announcements.py](backend/app/api/routes/announcements.py)
- 端点格式：`/ws/classroom/{session_id}`
- 支持课堂公告、问题发布和答题状态的实时推送
- 前端 WebSocket 客户端封装在 [frontend/src/api/websocket.ts](frontend/src/api/websocket.ts)

### 配置管理

- 默认配置：[config/default.yaml](config/default.yaml)
- 本机覆盖：[config/local.yaml](config/local.yaml)（不提交到版本控制）
- 配置加载和合并逻辑在 [backend/app/core/config.py](backend/app/core/config.py)
- 配置模型使用 Pydantic，支持类型验证

### 静态资源托管

- 前端构建产物放在 [frontend/dist/](frontend/dist/)
- [backend/app/main.py](backend/app/main.py) 会在启动时检测并托管 `dist` 目录
- 如果 `dist` 不存在，根路径返回提示信息

### AI 功能降级策略

- AI 配置管理在 [backend/app/services/ai.py](backend/app/services/ai.py)
- 启动时自动检测 AI 可用性（`/api/v1/system/startup`）
- AI 不可用时，基础功能（签到、答题、作业、统计）仍可正常使用
- 受影响功能：Excel 字段映射建议、简答题反馈、作业 AI 批阅、学习建议

## 开发约定

### 后端

1. **新增 API 路由**：在 [backend/app/api/routes/](backend/app/api/routes/) 下创建或修改路由文件，然后在 [backend/app/api/router.py](backend/app/api/router.py) 中注册
2. **服务层**：业务逻辑放在 [backend/app/services/](backend/app/services/) 下，保持路由处理器简洁
3. **数据库访问**：使用 `app.db.session.get_connection()` 获取连接，支持上下文管理器
4. **错误处理**：抛出 `AppError` 而非手动返回错误响应
5. **日志记录**：使用 `logging.getLogger(__name__)` 获取 logger，不要使用 `print()`
6. **敏感信息**：API Key、密码等不得写入日志或默认配置文件

### 前端

1. **路由**：新页面在 [frontend/src/routes/AppRouter.tsx](frontend/src/routes/AppRouter.tsx) 中注册
2. **API 调用**：使用 [frontend/src/api/http.ts](frontend/src/api/http.ts) 的 `request` 封装，不要直接使用 `fetch`
3. **状态管理**：全局状态用 Zustand（如 [frontend/src/store/authStore.ts](frontend/src/store/authStore.ts)）
4. **UI 组件**：使用 MUI 组件库，保持界面克制、清晰、工作台式风格
5. **WebSocket**：使用 [frontend/src/api/websocket.ts](frontend/src/api/websocket.ts) 的封装

### 通用

- 保持代码风格与现有项目一致
- 中文注释和文档优先（代码标识符使用英文）
- 不要创建营销页面，首页应是实际功能页面
- 修改后必须验证：后端运行 `compileall`，前端运行 `npm run build`

## 重要文档

开发前建议阅读：
- [README.md](README.md)：项目概览和快速开始
- [AGENTS.md](AGENTS.md)：项目背景和开发历程
- [docs/phase-1-delivery.md](docs/phase-1-delivery.md) ~ [docs/phase-10-delivery.md](docs/phase-10-delivery.md)：各阶段交付说明
- [docs/teacher-user-manual.md](docs/teacher-user-manual.md)：教师使用手册
- [docs/troubleshooting.md](docs/troubleshooting.md)：故障排查手册

需求和设计文档：
- `大学教学过程辅助软件需求分析报告_V2.md`
- `学教学过程辅助软件项目开发步骤与实施方案.md`

## 本地文件与目录

运行时自动创建的目录（位于教师机本地磁盘）：
- `C:\TeachingAssist\data\` - 数据库文件
- `C:\TeachingAssist\uploads\` - 用户上传文件
- `C:\TeachingAssist\backups\` - 数据库备份
- `C:\TeachingAssist\logs\` - 日志文件
- `C:\TeachingAssist\runtime\` - 运行时临时文件

开发环境产物（不提交）：
- `backend/.venv/` - Python 虚拟环境
- `frontend/node_modules/` - npm 依赖
- `frontend/dist/` - 构建产物

## 依赖安装优化

使用国内镜像加速：
```powershell
pip install -r backend\requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

## 注意事项

- PowerShell 中文输出可能乱码，读取 Markdown 时使用 `Get-Content -Encoding utf8`
- 前端开发代理配置在 [frontend/vite.config.ts](frontend/vite.config.ts)，自动转发 `/api` 和 `/ws` 到后端
- SQLite 连接参数固定：`journal_mode=WAL`、`synchronous=NORMAL`、`foreign_keys=ON`
- 项目已完成 10 个开发阶段，当前处于试点准备阶段
