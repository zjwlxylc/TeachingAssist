# 大学教学过程辅助软件

本仓库当前已完成“阶段 1：项目基础框架搭建”“阶段 2：系统管理与部署基础”和“阶段 3：课程、班级、课堂与学生导入”，提供可运行的 FastAPI 后端、React/Vite 前端、SQLite 初始化与迁移、教师认证、网卡端口检测、防火墙引导、数据库备份恢复基础能力、课前准备和学生名单导入能力。

## 技术栈

- 前端：React + Vite + TypeScript + MUI
- 后端：Python + FastAPI + Uvicorn
- 数据库：SQLite + WAL 模式
- 实时通信：前端 WebSocket 客户端封装已建立，后端业务通道后续阶段接入

## 项目结构

```text
backend/
  app/
    api/          REST API 路由
    core/         配置、日志、异常处理
    db/           SQLite 连接与迁移
    schemas/      统一响应模型
    services/     启动检查等服务
  run.py          Uvicorn 启动入口，含端口备选逻辑
  requirements.txt
frontend/
  src/
    api/          HTTP 与 WebSocket 客户端封装
    components/   通用 UI 组件
    layouts/      基础布局
    pages/        教师端和学生端页面
    routes/       前端路由
    store/        登录状态管理
config/
  default.yaml    默认配置
  local.example.yaml
scripts/
  init_db.py      数据库初始化脚本
docs/
```

## 后端开发

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:PYTHONPATH = (Get-Location).Path
python ..\scripts\init_db.py
python run.py
```

默认监听 `http://127.0.0.1:8080`。如 8080 被占用，启动脚本会尝试 8081、8888。

健康检查：

```text
GET /api/v1/health
GET /api/v1/system/startup
```

教师认证与系统管理：

```text
GET  /api/v1/auth/status
POST /api/v1/auth/setup
POST /api/v1/auth/login
GET  /api/v1/system/access
POST /api/v1/system/backups
```

课前准备：

```text
GET  /api/v1/academic/courses
POST /api/v1/academic/courses
GET  /api/v1/academic/classes
POST /api/v1/academic/classes
POST /api/v1/academic/sessions
POST /api/v1/academic/imports/excel
```

## 前端开发

```powershell
cd frontend
npm install
npm run dev
```

默认访问 `http://127.0.0.1:5173`，开发代理会将 `/api` 转发到后端 `http://127.0.0.1:8080`。

## 配置说明

默认配置位于 `config/default.yaml`。如需本机覆盖，复制 `config/local.example.yaml` 为 `config/local.yaml`。

数据库默认运行在教师机本地磁盘：

```text
C:\TeachingAssist\data\teaching_assist.db
```

启动时会自动创建：

- `C:\TeachingAssist\data`
- `C:\TeachingAssist\uploads`
- `C:\TeachingAssist\backups`
- `C:\TeachingAssist\logs`
- `C:\TeachingAssist\runtime`

SQLite 启动参数：

- `PRAGMA journal_mode=WAL`
- `PRAGMA synchronous=NORMAL`
- `PRAGMA foreign_keys=ON`

## 阶段 1 交付状态

- 可启动的后端服务：已完成
- 可访问的前端页面：已完成
- 数据库初始化脚本：已完成
- 基础配置文件：已完成
- 项目目录规范：已完成
- 开发环境说明文档：已完成

## 阶段 2 交付状态

- 教师首次设置密码与登录鉴权：已完成
- 教师端系统管理接口 Bearer Token 鉴权：已完成
- 网卡候选 IP、端口检测、访问地址生成：已完成
- Windows 防火墙引导命令：已完成
- 本地与可移动盘手动备份、自动备份、保留最近 5 份：已完成
- 备份恢复前安全副本：已完成

阶段说明见 `docs/phase-2-delivery.md`。

## 阶段 3 交付状态

- 创建课程、班级和课程班级关联：已完成
- 创建课堂并记录课次/补课标记：已完成
- `.xlsx` 学生名单上传、表头读取、样例展示：已完成
- 手动字段映射、校验预览、确认导入：已完成
- 学生数据可按课程用于后续签到校验：已完成

阶段说明见 `docs/phase-3-delivery.md`。
