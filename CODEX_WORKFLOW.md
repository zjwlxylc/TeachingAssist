# TeachingAssist Codex Workflow

本文件记录仓库长期执行约定。ALE v1.5.0 的完整规则见
`docs/agentic_loop_engineering.md`，当前机器状态见 `PROJECT_STATE.yaml`。

## 启动读取顺序

1. `AGENTS.md` 与当前目录下更深层指令；
2. `PROJECT_STATE.yaml`；
3. `CURRENT_ROUTE.md` 和它指向的最新验收包；
4. `CODEX_WORKFLOW.md`；
5. ALE Outcome 再读 `docs/agentic_loop_engineering.md`；
6. 当前实施计划、相关测试和必要业务文档；
7. Git 状态及 `python scripts/ale.py doctor`。

仓库事实与会话描述冲突时，以仓库和 Git 为准；不能安全消解时停止询问。

## 执行纪律

- 一次只推进一个当前 Outcome，不自动进入下一阶段。
- 先声明假设、范围、验证和停止条件，再修改文件。
- 行为变更执行真实 RED → minimal change → GREEN。
- 只修改与任务直接相关的行，保留用户已有改动。
- 只暂存精确文件，不使用 `git add .`。
- 未经明确授权不 push、不 merge 主线、不删除分支或 worktree。
- 中文 Markdown 使用 UTF-8 读取和写入。
- 不提交 API Key、密码、令牌、个人路径、数据库或学生个人信息。

## TeachingAssist 风险边界

- 前端保持 React + Vite + TypeScript + MUI，不无故升级 Node 或依赖。
- 后端保持 FastAPI、SQLite 和现有统一响应/错误约定。
- 数据库变更只能追加 SQL migration，不修改已应用 migration。
- 无外网或 AI 不可用时，基础课堂功能必须继续可用。
- 产品运行时、本机配置和自检隔离数据必须分开。

## 仓库验证入口

```powershell
.\.venv\Scripts\python.exe scripts\ale.py doctor
.\.venv\Scripts\python.exe scripts\ale.py focused --target control-plane
.\.venv\Scripts\python.exe scripts\ale.py focused --target backend
.\.venv\Scripts\python.exe scripts\ale.py focused --target frontend
.\.venv\Scripts\python.exe scripts\ale.py exit
```

控制面工具尚未建立时，直接使用现有命令：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\selftest_smoke.py
Set-Location frontend
npm.cmd run build
```

自动检查通过后必须生成书面验收包并停在人工门，不能自行宣布接受。
