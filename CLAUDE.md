# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概况

这是一个面向高校机房课堂教学场景的 B/S 架构教学辅助系统。后端运行于教师机，学生通过局域网内浏览器访问。系统支持学生导入、签到、公告、问答、作业、课堂互动、师生私信、AI 课堂对话、AI 辅助反馈、学习效果评估和备份恢复等功能。

**核心部署约束**：
- 程序和配置可放在 U 盘
- 数据库必须位于教师机本地磁盘（默认 `C:\TeachingAssist\data\teaching_assist.db`）
- SQLite 使用 WAL 模式和 `synchronous=NORMAL`
- 支持无外网或 AI 不可用时的基础功能降级

**当前状态**：已完成阶段 1-10，并通过全模块四维度自检三迭代闭环（详见 `docs/selftest-3iteration-report.md`）

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

类型检查：
```powershell
cd frontend
npx tsc --noEmit
```

### 健康检查

```powershell
curl.exe http://127.0.0.1:8080/api/v1/health
curl.exe http://127.0.0.1:8080/api/v1/system/startup
```

### 主要 API 端点

**认证与系统管理：**
```text
GET  /api/v1/auth/status
POST /api/v1/auth/setup
POST /api/v1/auth/login
GET  /api/v1/system/access
POST /api/v1/system/backups
```

**课前准备：**
```text
GET  /api/v1/academic/courses
POST /api/v1/academic/courses
GET  /api/v1/academic/classes
POST /api/v1/academic/classes
POST /api/v1/academic/sessions
POST /api/v1/academic/imports/excel
```

**课堂互动发言：**
```text
GET  /api/v1/interactions/sessions/{session_id}/settings
PUT  /api/v1/interactions/sessions/{session_id}/settings
GET  /api/v1/interactions/sessions/{session_id}/messages
POST /api/v1/interactions/sessions/{session_id}/messages/teacher
POST /api/v1/interactions/sessions/{session_id}/messages/student
GET  /api/v1/interactions/sessions/{session_id}/moderation/logs
POST /api/v1/interactions/sessions/{session_id}/moderation/{log_id}/approve
POST /api/v1/interactions/sessions/{session_id}/moderation/{log_id}/reject
```

**师生私信：**
```text
POST /api/v1/messages                      # 学生发送私信（令牌优先）
GET  /api/v1/messages/mine                 # 学生查看私信会话
POST /api/v1/messages/mine/read            # 学生标记已读
GET  /api/v1/messages/conversations        # 教师查看会话列表
GET  /api/v1/messages/students/{student_id} # 教师查看与某学生的私信
POST /api/v1/messages/students/{student_id}/reply # 教师回复学生
GET  /api/v1/messages/unread-count         # 教师未读数
WS   /ws/messages                          # 私信实时推送（强制令牌认证）
```

### 打包部署

Windows 可执行程序打包：
```powershell
# 安装构建依赖
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-build.txt

# 打包（生成 .runtime\release\TeachingAssist-{版本号}）
.\scripts\build_release.ps1 -Version 0.1.0

# 仅验证目录结构，不执行 PyInstaller
.\scripts\build_release.ps1 -Version 0.1.0 -SkipPyInstaller
```

生成 U 盘部署包：
```powershell
# 在部署包目录中执行，将文件复制到 U 盘
.\scripts\make_usb_package.ps1 -TargetRoot E:\
```

U 盘目录结构：
```text
TeachingAssist/
  TeachingAssist.exe
  start_teaching_assist.bat
  config/
    default.yaml
    local.yaml
  frontend/dist/
  backup/
  docs/
```

## 架构要点

### 三迭代自检闭环（重要）

项目已完成全模块四维度自检（错误检测、操作流程、前端显示、数据库自检），并通过三次完整迭代，详见 [docs/selftest-3iteration-report.md](docs/selftest-3iteration-report.md)。关键改进包括：

**迭代 1 - 模块级修复：**
- 备份同秒覆盖问题：添加 UUID 后缀
- WebSocket 单卡拖垮整组：添加 5 秒发送超时
- WebSocket 空闲无超时：添加 300 秒空闲断开
- AI 事务内调用（SQLite 锁反模式）：重构为三阶段（只读 → 关连接 → 事务外调 AI → 新连接写）
- 作业重复批阅回退状态：筛选排除已批阅状态
- 前端 AppSnackbar 全失效：移除硬编码，使用 MUI severity
- 补充 10 个高频查询索引

**迭代 2 - 架构级深化：**
- **读路径写副作用**：`get_session_public`/`list_active_sessions` 改为纯读，状态刷新改为后台定时任务（每 60 秒）
- **AI 超时预算**：AI 课堂对话添加 40 秒总体超时守卫，超时优雅降级
- **API Key 加密**：使用 Fernet 加密存储（`enc::` 前缀），向后兼容明文
- **学生令牌认证**：签到时颁发会话令牌，私信/作业反馈/草稿读取强制使用令牌（防冒名）

**迭代 3 - 深层闭环：**
- 私信强制令牌：移除学号+姓名兜底（冒名风险）
- PII 读取令牌优先：作业反馈、评估反馈、答题草稿改为令牌优先（服务端保留学号+姓名兜底供 AI 课堂复用）
- GET 标记已读改为 POST：`POST /messages/mine/read` 避免读路径写副作用
- 作业提交文本长度校验：后端 5000 字符上限
- API Key 掩码固定：`****` 不泄露首尾片段

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
- 学生端基础操作通过学号和姓名双因子验证（不需要预注册）
- 学生隐私操作（私信、作业反馈、草稿读取）使用会话令牌（签到时自动颁发，存储在 `student_sessions` 表）
- 初次启动需要教师设置密码（`POST /api/v1/auth/setup`）
- API Key 使用 Fernet 加密存储（`enc::` 前缀，向后兼容明文）

### WebSocket 实时推送

- WebSocket 路由定义在 [backend/app/api/routes/announcements.py](backend/app/api/routes/announcements.py) 和 [backend/app/api/routes/messages.py](backend/app/api/routes/messages.py)
- 课堂公告端点：`/ws/classroom/{session_id}`（学生端，基于学号+姓名）
- 师生私信端点：`/ws/messages`（学生端，强制令牌认证）
- 支持课堂公告、问题发布、答题状态和私信的实时推送
- WebSocket 连接设置：
  - 单消息发送超时：5 秒（防止单个慢连接拖垮广播）
  - 空闲连接超时：300 秒（5 分钟无活动自动断开）
- 前端 WebSocket 客户端封装在 [frontend/src/api/websocket.ts](frontend/src/api/websocket.ts)，支持断线重连（指数退避）

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
- AI 课堂对话设置了整体超时预算（40 秒），超时优雅降级

### 后台定时任务

为避免读路径产生写副作用，以下操作改为后台定时执行：
- 课堂状态自动刷新：每 60 秒检查课堂状态（pending → active → ended）
- 自动备份：按配置的时间间隔执行（使用 `run_in_executor` 避免阻塞事件循环）

## 开发约定

### 后端

1. **新增 API 路由**：在 [backend/app/api/routes/](backend/app/api/routes/) 下创建或修改路由文件，然后在 [backend/app/api/router.py](backend/app/api/router.py) 中注册
2. **服务层**：业务逻辑放在 [backend/app/services/](backend/app/services/) 下，保持路由处理器简洁
3. **数据库访问**：使用 `app.db.session.get_connection()` 获取连接，支持上下文管理器
4. **错误处理**：抛出 `AppError` 而非手动返回错误响应
5. **日志记录**：使用 `logging.getLogger(__name__)` 获取 logger，不要使用 `print()`
6. **敏感信息**：API Key、密码等不得写入日志或默认配置文件；API Key 存储时使用 Fernet 加密
7. **AI 调用**：禁止在数据库事务内调用 AI（SQLite 锁反模式），应该先关闭连接，调用 AI，再开新连接写入结果
8. **读路径副作用**：GET 接口不应产生写副作用（如状态更新、备份触发），写操作应通过 POST 端点或后台定时任务执行

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
- [docs/selftest-3iteration-report.md](docs/selftest-3iteration-report.md)：**全模块四维度自检闭环报告（必读）**
- [docs/teacher-user-manual.md](docs/teacher-user-manual.md)：教师使用手册
- [docs/deployment-checklist.md](docs/deployment-checklist.md)：部署检查清单
- [docs/troubleshooting.md](docs/troubleshooting.md)：故障排查手册
- [docs/pilot-feedback-report.md](docs/pilot-feedback-report.md)：试点反馈报告模板

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
- 项目已完成 10 个开发阶段，并通过三迭代自检闭环，当前处于试点准备阶段

## 自检与测试

### 冒烟测试

```powershell
# 使用隔离测试环境（.selftest 目录）
python scripts\selftest_smoke.py
```

测试覆盖：
- 认证/系统/备份/恢复（鉴权、备份完整性、访问地址持久化）
- 课前准备/课堂/公告/私信（WebSocket 超时、令牌认证、消息推送）
- 问答/互动/作业/评估（AI 事务外调用、作业状态、填空题判分）
- AI 管理/聊天（API Key 加密、结构化 JSON、超时控制）
- 前端（类型检查、构建验证）

### 隔离测试环境

创建 `config/local.yaml` 并覆盖存储路径：

```yaml
storage:
  local_root: D:/Agent/TeachingAssist-main/.selftest
```

这样测试数据不会污染真实的 `C:\TeachingAssist` 目录。

### 前端验证

```powershell
cd frontend
npx tsc --noEmit
npm run build
```
