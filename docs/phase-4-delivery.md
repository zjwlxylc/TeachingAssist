# 阶段 4 交付说明

## 已完成

1. 课堂状态机接入 `pending`、`active`、`ended` 三种状态。
2. 教师端支持手动开始课堂，开始前校验本课堂已导入学生名单。
3. 教师端支持手动结束课堂，结束后状态不可逆。
4. 支持按 `start_time` 自动开始课堂，按 `end_time` 自动结束课堂。
5. 课堂结束时自动为未签到学生生成 `absent` 缺勤记录。
6. 课堂结束时触发 `class_ended` 数据库备份。
7. 课堂结束时初始化学习效果评价占位任务，供后续阶段接入。
8. 学生端支持课堂 ID 查询、活动课堂选择、学号与姓名双因子签到。
9. 签到记录保存 IP、User-Agent、签到时间和状态。
10. 同一学生同一课堂只允许一条签到记录，重复提交返回已有记录。
11. 根据课堂开始时间和默认 15 分钟截止时间判断正常签到或迟到。
12. 教师端可查看课堂签到统计和学生明细。

## 新增接口

```text
POST /api/v1/classroom/sessions/{session_id}/start
POST /api/v1/classroom/sessions/{session_id}/end
GET  /api/v1/classroom/sessions/{session_id}/sign-ins
GET  /api/v1/classroom/sessions/active/list
GET  /api/v1/classroom/sessions/{session_id}
POST /api/v1/classroom/sessions/{session_id}/sign-in
```

教师操作接口需要 Bearer Token；学生查询与签到接口面向课堂局域网访问。

## 数据库变更

新增迁移：`backend/app/db/migrations/004_classroom_signin.sql`

- `classroom_sessions.actual_started_at`：课堂实际开始时间。
- `classroom_sessions.actual_ended_at`：课堂实际结束时间。
- `classroom_sessions.ended_by`：结束来源，支持教师或自动结束。
- `sign_in_records`：学生签到、迟到、缺勤记录，唯一约束为 `(session_id, student_id)`。
- `evaluation_tasks`：课后学习效果评价任务占位表，后续阶段继续扩展。

## 验证记录

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成 API 烟测：

- 创建课程、班级、课堂。
- 上传 `.xlsx` 学生名单并导入 2 名学生。
- 教师手动开始课堂，课堂状态变为 `active`。
- 学生正常签到成功。
- 同一学生重复签到返回已有记录。
- 学号正确但姓名错误返回 `STUDENT_NAME_MISMATCH`。
- 教师结束课堂后，未签到学生自动标记为 `absent`。
- 课堂结束后继续签到返回 `SESSION_ENDED`。

## 留待后续阶段

- 课堂公告、课堂问答、作业发布与提交按实施方案后续阶段继续。
- 学习效果评价当前仅初始化任务占位，评价指标、计算和展示将在后续阶段实现。
- 实时推送可在 WebSocket 业务通道阶段进一步增强，目前教师端通过刷新统计查看近实时数据。
