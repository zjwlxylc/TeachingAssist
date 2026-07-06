# AGENTS.md

本文件用于帮助 Codex 或其他自动化开发代理在新窗口、重新运行或后续阶段开发时快速接手本项目。

## 项目概况

项目名称：大学教学过程辅助软件

项目目标：面向高校机房课堂教学场景，建设可在局域网内独立运行的 B/S 架构教学过程辅助系统。后端运行于教师机，学生通过浏览器访问。系统围绕学生导入、签到、公告、问答、作业、过程数据采集、AI 辅助反馈、学习效果评估、备份恢复形成教学闭环。

核心部署原则：

- 程序和配置可放在 U 盘。
- 运行时数据库必须位于教师机本地磁盘，默认 `C:\TeachingAssist\data\teaching_assist.db`。
- SQLite 开启 WAL 模式和 `synchronous=NORMAL`。
- 课后和定时备份到本地与 U 盘目录。
- 无外网或 AI 不可用时，签到、答题、作业、成绩统计等基础功能必须可用。

## 重要文档

优先阅读以下文档：

- `大学教学过程辅助软件需求分析报告_V2.md`
- `学教学过程辅助软件项目开发步骤与实施方案.md`
- `README.md`
- `docs/phase-1-delivery.md`
- `docs/phase-2-delivery.md`
- `docs/phase-3-delivery.md`

当前已完成：

- 阶段 1：项目基础框架搭建
- 阶段 2：系统管理与部署基础
- 阶段 3：课程、班级、课堂与学生导入

后续应按实施方案阶段继续推进，通常下一步是：

- 阶段 4：课堂状态机与签到系统

## 技术栈

后端：

- Python
- FastAPI
- Uvicorn
- SQLite
- SQL 文件迁移
- PyYAML 配置加载

前端：

- React
- Vite
- TypeScript
- MUI
- React Router
- Zustand

当前本机环境曾验证：

- Python 3.13.2
- Node 16.19.1
- npm 8.19.3

注意：当前 Node 版本较旧，前端依赖已固定为兼容 Node 16 的 Vite 4 / MUI 5 组合。不要随意升级到要求 Node 18+ 的新版 Vite 或相关依赖，除非同时升级本机 Node。

## 项目结构

```text
backend/
  app/
    api/
      routes/          API 路由
      router.py        API 聚合路由
    core/
      config.py        配置加载
      exceptions.py    全局异常处理
      logging.py       日志配置
    db/
      migrations/      SQL 迁移文件
      migrations.py    迁移执行与完整性检查
      session.py       SQLite 连接
    schemas/
      response.py      统一 API 响应模型
    services/
      auth.py          教师密码、登录令牌与鉴权服务
      academic.py      课程、班级、课堂与学生导入服务
      backup.py        本地与可移动盘备份、恢复服务
      network.py       网卡候选地址、端口与防火墙引导
      startup.py       启动检查、目录初始化、U 盘路径识别、自动备份任务
    main.py            FastAPI 应用入口
  run.py               Uvicorn 启动入口，含端口备选逻辑
  requirements.txt

frontend/
  src/
    api/               HTTP 与 WebSocket 客户端封装
    components/        通用组件
    layouts/           页面布局
    pages/             教师端、学生端页面
    routes/            前端路由
    store/             Zustand 状态管理
    styles/            MUI 主题
  package.json
  vite.config.ts

config/
  default.yaml         默认配置
  local.example.yaml   本机覆盖配置示例

scripts/
  init_db.py           数据库初始化脚本

docs/
  phase-1-delivery.md  阶段 1 交付说明
  phase-2-delivery.md  阶段 2 交付说明
  phase-3-delivery.md  阶段 3 交付说明
```

## 后端运行

首次运行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
$env:PYTHONPATH = (Resolve-Path backend).Path
python scripts\init_db.py
```

启动后端：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
cd backend
python run.py
```

也可直接指定端口：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8080
```

健康检查：

```text
GET http://127.0.0.1:8080/api/v1/health
GET http://127.0.0.1:8080/api/v1/system/startup
```

## 前端运行

```powershell
cd frontend
npm install
npm run dev
```

默认访问：

```text
http://127.0.0.1:5173
```

前端开发代理会将 `/api` 转发到：

```text
http://127.0.0.1:8080
```

构建验证：

```powershell
cd frontend
npm run build
```

## 依赖安装建议

Python 第三方库安装可优先使用国内镜像，例如阿里或清华，以提升速度。

示例：

```powershell
pip install -r backend\requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

或：

```powershell
pip install -r backend\requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple/
```

npm 如遇下载慢，可考虑设置国内 registry，但不要无故改动锁文件版本。

## 阶段 1 已完成能力

后端：

- FastAPI 项目结构
- Uvicorn 启动入口
- SQLite 数据库连接
- WAL 模式配置
- SQL 迁移机制
- 启动时目录初始化
- 启动时 `PRAGMA integrity_check`
- 统一响应格式：`success/code/message/data`
- 全局异常处理
- 日志系统
- 配置文件加载
- 前端构建产物静态托管
- 健康检查接口
- 启动检查接口

前端：

- React + Vite + TypeScript 项目
- MUI 主题
- 教师端路由
- 学生端路由
- 基础布局
- API 请求封装
- WebSocket 客户端封装
- 登录状态 store
- 错误提示组件

## 后续开发建议

下一阶段建议优先实现：

1. 教师首次设置密码。
2. 教师登录与接口鉴权。
3. 网卡枚举与候选 IP 选择。
4. 端口冲突检测与访问地址生成。
5. 防火墙引导说明。
6. 本地与 U 盘备份目录初始化。
7. 手动备份、自动备份、保留最近 5 份备份。

阶段 2 对应需求重点：

- SYS-AUTH-01
- SYS-AUTH-02
- SYS-NET-01
- SYS-NET-02
- SYS-NET-03
- SYS-DEP-01
- SYS-DEP-02

## 开发约定

- 保持代码和目录结构与现有项目风格一致。
- 后端新增接口应返回统一 `ApiResponse`。
- 后端业务错误优先使用 `AppError`。
- 数据库结构变更通过 `backend/app/db/migrations/*.sql` 追加迁移，不直接修改已应用迁移。
- SQLite 连接应继续统一走 `app.db.session.get_connection()` 或同层封装。
- 配置项优先加入 `config/default.yaml` 和 `AppSettings`，本机差异放 `config/local.yaml`。
- 不要把 API Key、密码、个人路径等敏感信息写入日志或提交到配置默认文件。
- 前端新增页面应纳入 `frontend/src/routes/AppRouter.tsx`。
- 前端 API 调用优先使用 `frontend/src/api/http.ts` 的 `request` 封装。
- UI 使用 MUI，保持面向教学管理工具的克制、清晰、工作台式界面。
- 不要做营销落地页；应用首页应是可用的教师端或学生端功能。

## 验证清单

后端修改后建议运行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\init_db.py
```

前端修改后建议运行：

```powershell
cd frontend
npm run build
```

接口验证：

```powershell
curl.exe http://127.0.0.1:8080/api/v1/health
curl.exe http://127.0.0.1:8080/api/v1/system/startup
```

阶段 2 认证与系统管理接口：

```text
GET  /api/v1/auth/status
POST /api/v1/auth/setup
POST /api/v1/auth/login
GET  /api/v1/system/access
POST /api/v1/system/backups
```

阶段 3 课前准备接口：

```text
GET  /api/v1/academic/courses
POST /api/v1/academic/courses
GET  /api/v1/academic/classes
POST /api/v1/academic/classes
POST /api/v1/academic/course-classes
GET  /api/v1/academic/sessions
POST /api/v1/academic/sessions
POST /api/v1/academic/imports/excel
POST /api/v1/academic/imports/{job_id}/preview
POST /api/v1/academic/imports/{job_id}/confirm
```

## 运行中产生的本地文件

以下内容是本机运行产物，通常不应作为业务代码依赖：

- `.venv/`
- `frontend/node_modules/`
- `frontend/dist/`
- `.runtime/`
- `C:\TeachingAssist\data\teaching_assist.db`
- `C:\TeachingAssist\logs\`

如果后续建立 Git 仓库，应将这些目录加入 `.gitignore`。

## 注意事项

- 当前环境可能没有 `git` 命令，不要假设可以使用 `git status` 或 `git diff`。
- PowerShell 默认编码有时会导致中文输出乱码，读取中文 Markdown 时使用 `Get-Content -Encoding utf8`。
- 如果启动前端时根路径短暂返回异常，优先用 `curl.exe http://127.0.0.1:5173/` 或浏览器验证；此前 Vite 日志显示服务正常。
- 后端配置中的 `app_name` 中文在某些 PowerShell JSON 输出里可能显示为乱码，但 HTTP 实际响应和前端显示正常。
