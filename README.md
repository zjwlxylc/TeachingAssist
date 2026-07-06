# 大学教学过程辅助软件

本仓库当前已完成“阶段 1：项目基础框架搭建”“阶段 2：系统管理与部署基础”“阶段 3：课程、班级、课堂与学生导入”“阶段 4：课堂状态机与签到系统”“阶段 5：课堂公告与 WebSocket 实时通信”“阶段 6：课堂互动问答 P0”和“阶段 7：作业管理 P0”，提供可运行的 FastAPI 后端、React/Vite 前端、SQLite 初始化与迁移、教师认证、网卡端口检测、防火墙引导、数据库备份恢复基础能力、课前准备、学生名单导入、课堂开始/结束、学生签到、课堂公告、实时推送、课堂问答发布、学生答题、自动判分、教师统计、作业发布、学生提交和教师查看作业提交列表能力。

## 技术栈

- 前端：React + Vite + TypeScript + MUI
- 后端：Python + FastAPI + Uvicorn
- 数据库：SQLite + WAL 模式
- 实时通信：WebSocket 已接入课堂公告、问题发布和答题状态推送

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

## 阶段 4 交付状态

- 课堂 `pending`、`active`、`ended` 状态机：已完成
- 教师手动开始/结束课堂：已完成
- 按计划时间自动开始/结束课堂：已完成
- 学生学号与姓名双因子签到：已完成
- 签到唯一约束、IP、User-Agent、迟到判断：已完成
- 课堂结束自动标记缺勤、触发备份、初始化评价任务：已完成
- 教师端签到统计和学生端签到入口：已完成

阶段说明见 `docs/phase-4-delivery.md`。

## 阶段 5 交付状态

- 课堂 WebSocket 通道：已完成
- 教师发布课堂公告：已完成
- 公告先入库再推送：已完成
- 学生端历史公告和实时公告接收：已完成
- 基于 `last_message_id` 的断线增量补拉：已完成

阶段说明见 `docs/phase-5-delivery.md`。

## 阶段 6 交付状态

- 教师发布单选、多选、判断、填空、简答题：已完成
- 问题通过课堂 WebSocket 实时推送：已完成
- 学生端查看问题并在线作答：已完成
- 答案保存、版本记录和行为日志：已完成
- 单选、多选、判断、填空自动判分：已完成
- 教师查看提交数、正确率、选项分布和典型答案：已完成

阶段说明见 `docs/phase-6-delivery.md`。

## 阶段 7 交付状态

- 教师发布作业、填写说明、截止时间、评分标准：已完成
- 作业截止时间校验：已完成
- 学生提交文本和常见格式附件：已完成
- 作业多次提交版本管理和最新版本标记：已完成
- 截止后禁止提交或标记迟交：已完成
- 教师查看提交列表、未交/已交/迟交统计、文本和附件元数据：已完成

阶段说明见 `docs/phase-7-delivery.md`。
