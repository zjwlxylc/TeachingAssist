# 阶段 8 交付说明

## 已完成

1. 新增 AI Provider 配置数据模型，支持 provider 标识、显示名称、base_url、模型名称、API Key、HTTP Proxy、启用状态和当前激活项。
2. API Key 仅后端保存，教师端和接口返回均只显示是否已配置及脱敏掩码。
3. 启动检查接入 AI 连通性自检，AI 未启用或不可用时进入基础模式，不影响签到、答题、作业提交和统计。
4. 教师端支持查看 AI 状态、配置 Provider、切换 Provider、手动触发连通性自检。
5. 新增 AI 分级降级策略与失败任务入口，覆盖 Excel 字段映射、简答题反馈、作业批阅和学习建议四类场景。
6. 新增 AI 内容安全策略，支持最大长度限制、关键词替换或拦截、教师审核后展示或直接展示并举报两种展示策略。
7. 新增内容安全检查日志和 AI 自检日志，避免在日志中输出 API Key 明文。

## 新增接口

```text
GET  /api/v1/ai/overview
POST /api/v1/ai/providers
PUT  /api/v1/ai/providers/{provider_id}
POST /api/v1/ai/providers/{provider_id}/activate
POST /api/v1/ai/check
PUT  /api/v1/ai/safety
POST /api/v1/ai/safety/check
GET  /api/v1/ai/failure-tasks
POST /api/v1/ai/failure-tasks
```

以上接口均需教师 Bearer Token。

## 数据库变更

新增迁移：`backend/app/db/migrations/008_ai_management.sql`

- `ai_provider_configs`：保存多 Provider 配置、启用状态和最近自检状态。
- `ai_check_logs`：记录 AI 连通性自检结果。
- `ai_safety_settings`：保存内容安全策略。
- `ai_content_safety_logs`：记录内容安全检查结果。
- `ai_failure_tasks`：保存 AI 失败后的人工处理或模板生成任务。

## 教师端能力

- AI 管理与安全面板显示当前 AI 可用状态和基础模式提示。
- 可配置 DeepSeek、智谱 GLM、通义千问、OpenAI 等 Provider 默认项。
- 可设置 API Key、base_url、模型名称、HTTP Proxy 和启用状态。
- 可查看受 AI 不可用影响的功能范围。
- 可配置敏感关键词、处理方式、最大长度和展示策略。
- 可用测试文本验证内容安全处理结果。

## 验证记录

已执行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成服务层烟测：

- `get_ai_overview()` 可读取默认 Provider 和基础模式状态。
- 启动初始化自动应用 `008_ai_management` 迁移。
- AI 未启用时自检记录为 `disabled`，并返回基础模式提示。
- `check_content_safety()` 可执行并记录安全检查日志。
- `record_failure_task("homework_review")` 可生成待人工处理任务。

## 留待后续阶段

- 阶段 9 继续实现 P1 增强：导入增强、签到增强、问答增强、作业 AI 批阅与成绩发布、学习评估。
- 简答题 AI 反馈、作业 AI 批阅和学习建议生成会复用本阶段的 Provider、自检、降级任务和内容安全服务。
