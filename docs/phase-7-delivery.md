# 阶段 7 交付说明

## 已完成

1. 新增作业管理数据模型，支持作业、作业附件、学生提交、提交附件和后续批阅记录扩展。
2. 教师端支持选择课堂发布作业，填写标题、说明、截止时间、评分标准和是否允许迟交。
3. 后端校验作业截止时间必须晚于发布时间。
4. 学生端进入课堂后可查看公开作业列表。
5. 学生可提交文本内容和常见格式附件。
6. 学生可在截止前多次提交，系统保留历史版本并标记最新版本。
7. 截止后禁止提交或按作业配置标记为迟交。
8. 教师端支持查看作业提交列表，区分未提交、已提交和迟交，并展示提交时间、版本、文本内容和附件元数据。

## 新增接口

```text
POST /api/v1/homework/sessions/{session_id}
GET  /api/v1/homework/sessions/{session_id}
GET  /api/v1/homework/sessions/{session_id}/public
POST /api/v1/homework/{homework_id}/submissions
GET  /api/v1/homework/{homework_id}/submissions
```

教师发布作业、查看教师作业列表和查看提交列表需要 Bearer Token；学生查询公开作业和提交作业面向课堂局域网访问。

## 文件上传规则

- 单文件大小上限：10MB。
- 支持扩展名：`.doc`、`.docx`、`.pdf`、`.zip`、`.txt`、`.jpg`、`.jpeg`、`.png`。
- 文件保存目录：`C:\TeachingAssist\uploads\homework\{homework_id}\submissions\{submission_id}`。
- 当前阶段保存附件元数据供教师查看；下载、导出和批阅属于后续增强。

## 数据库变更

新增迁移：`backend/app/db/migrations/007_homework_management.sql`

- `homework`：保存作业标题、说明、截止时间、评分标准、状态和迟交策略。
- `homework_attachments`：预留作业附件表。
- `homework_submissions`：保存学生提交、状态、版本号和最新版本标记。
- `homework_submission_files`：保存学生提交附件元数据。
- `homework_review_records`：预留 AI 或教师批阅记录表。

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

- 创建课程、班级、课堂并写入测试学生。
- 启动课堂后发布未来截止时间作业。
- 学生第一次提交文本成功。
- 学生第二次提交文本和 `.txt` 附件成功，最新版本为 v2。
- 教师提交列表显示应交 1 人、已交 1 人、附件 1 个。
- 过期截止时间的作业发布被拒绝。
- 允许迟交的作业在截止后提交会标记为 `late`。
- 禁止迟交的作业在截止后提交会被拒绝。

## 留待后续阶段

- AI 作业批阅、自动评分、教师复核、成绩发布和学生查看反馈属于 P1 作业增强。
- 作业下载、导出和批量归档属于后续增强。
- 下一阶段按实施方案进入“阶段 8：AI 管理、降级与内容安全”。
