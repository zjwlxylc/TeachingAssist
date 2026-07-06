# 阶段 9 交付说明

## 已完成

1. 学生导入增强：支持 AI/本地字段映射建议、错误报告 CSV 导出、重复学号增量合并/覆盖/跳过策略，以及学生停用和启用。
2. 签到增强：支持签到数据导出、教师手动补签、签到状态修改和修改日志追踪。
3. 问答增强：支持简答题 AI 反馈、失败降级任务、问答加分计算、答案 CSV 导出、匿名统计和学生答题草稿恢复。
4. 作业增强：支持教师附件上传、AI 结构化批阅、教师复核、成绩发布、学生查看反馈和提交结果导出。
5. 学习效果评估：支持单堂课临时/最终评估，多指标加权、自动分级、教师报表、学生个人反馈、异常预警和评估 CSV 导出。
6. 恢复增强：学生端断线期间缓存文本类答题/作业请求，重连后批量重发并记录；教师可记录中断事件、延长答题截止或重新开放签到窗口。

## 新增接口

```text
POST /api/v1/academic/imports/{job_id}/mapping-suggestion
GET  /api/v1/academic/imports/{job_id}/errors.csv
PUT  /api/v1/academic/students/{student_pk}/active

PUT  /api/v1/classroom/sessions/{session_id}/sign-ins/status
GET  /api/v1/classroom/sessions/{session_id}/sign-ins/logs
GET  /api/v1/classroom/sessions/{session_id}/sign-ins.csv

GET  /api/v1/questions/{question_id}/stats/anonymous
POST /api/v1/questions/{question_id}/draft
GET  /api/v1/questions/sessions/{session_id}/answers.csv
GET  /api/v1/questions/sessions/{session_id}/bonus
GET  /api/v1/questions/bonus/settings
PUT  /api/v1/questions/bonus/settings

POST /api/v1/homework/{homework_id}/attachments
POST /api/v1/homework/{homework_id}/ai-review
PUT  /api/v1/homework/submissions/{submission_id}/review
POST /api/v1/homework/{homework_id}/publish-grades
POST /api/v1/homework/{homework_id}/feedback
GET  /api/v1/homework/{homework_id}/submissions.csv

POST /api/v1/evaluation/sessions/{session_id}/calculate
GET  /api/v1/evaluation/sessions/{session_id}
PUT  /api/v1/evaluation/weights
POST /api/v1/evaluation/sessions/{session_id}/student-feedback
GET  /api/v1/evaluation/sessions/{session_id}.csv

POST /api/v1/recovery/sessions/{session_id}/interruptions
POST /api/v1/recovery/sessions/{session_id}/actions
POST /api/v1/recovery/sessions/{session_id}/cached-replays
GET  /api/v1/recovery/sessions/{session_id}/events
```

教师管理、导出和配置类接口均需教师 Bearer Token；学生反馈、草稿查询和缓存重放接口面向学生端开放。

## 数据库变更

新增迁移：`backend/app/db/migrations/009_p1_enhancements.sql`

- `student_import_reports`：记录导入错误报告。
- `sign_in_change_logs`：记录补签和签到状态变更。
- `question_bonus_settings`、`question_bonus_records`：保存问答加分规则和学生加分明细。
- `homework_review_jobs`：记录作业 AI 批阅任务。
- `evaluation_weight_settings`、`learning_evaluations`：保存学习评估权重和临时/最终版本。
- `recovery_events`：记录中断事件、恢复动作和缓存请求重放。
- 扩展问答答案与作业提交表，保存草稿、AI 反馈、加分、AI 批阅、教师复核和成绩发布字段。

## 前端能力

- 教师端新增导入映射建议、重复策略、错误报告、学生停启用、签到补签和修改日志入口。
- 教师端新增问答加分规则、匿名统计、答案导出、作业附件、AI 批阅、教师复核、成绩发布和导出入口。
- 教师端新增学习评估与恢复面板，可生成临时/最终评估、导出报告、记录中断并应用恢复动作。
- 学生端新增答题草稿保存/恢复、离线文本请求缓存与重放、作业成绩反馈和课堂学习反馈查看。

## 验证记录

已执行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

验证结果：

- 后端编译通过。
- 数据库初始化通过，并成功应用 `009_p1_enhancements` 迁移。
- 前端 TypeScript 与 Vite 生产构建通过。

## 留待后续阶段

- 阶段 10 进入打包、部署与试点：前端静态资源构建、后端可执行程序、启动器、U 盘目录、教师手册、部署检查清单、故障排查手册和试点反馈报告。
