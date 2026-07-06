# 阶段 6 交付说明

## 已完成

1. 新增课堂问答数据模型，支持问题、选项、答案版本和行为日志。
2. 教师端支持在活动课堂发布单选、多选、判断、填空和简答题。
3. 问题发布后通过既有课堂 WebSocket 通道实时推送给学生端。
4. 学生端进入课堂后可查看历史问题，并可按题型在线作答。
5. 学生答题提交会保存最新答案版本，并记录答题行为日志。
6. 单选、多选、判断题支持自动判分。
7. 填空题支持标准答案精确匹配和关键词包含匹配。
8. 教师端支持查看提交人数、正确人数、正确率、选项分布和典型文本答案。

## 新增接口

```text
POST /api/v1/questions/sessions/{session_id}
GET  /api/v1/questions/sessions/{session_id}
GET  /api/v1/questions/sessions/{session_id}/public
POST /api/v1/questions/{question_id}/answers
GET  /api/v1/questions/{question_id}/stats
WS   /ws/classroom/{session_id}
```

教师发布问题、查看教师题目列表和查看统计接口需要 Bearer Token；学生查询公开问题和提交答案面向课堂局域网访问。

## WebSocket 消息

```json
{
  "type": "question.published",
  "session_id": 1,
  "question": {}
}
```

```json
{
  "type": "question.answer.updated",
  "session_id": 1,
  "question_id": 1,
  "student_id": "20240001",
  "status": "submitted"
}
```

## 数据库变更

新增迁移：`backend/app/db/migrations/006_questions_answers.sql`

- `questions`：保存课堂问题、题型、状态、标准答案、关键词、分值和截止时间。
- `question_options`：保存选择题和判断题选项。
- `question_answers`：保存学生答案、提交状态、自动判分结果和答案版本。
- `question_action_logs`：保存发布、开始答题、草稿、提交等行为日志。

## 验证记录

已执行：

```powershell
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe -m compileall backend\app
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成 API/WebSocket 烟测：

- 创建课程、班级、课堂并写入测试学生。
- 启动课堂后建立 `/ws/classroom/{session_id}` 连接。
- 教师发布单选题成功。
- WebSocket 客户端收到 `question.published` 消息。
- 学生提交正确答案成功。
- 教师统计显示提交人数 1、正确人数 1、正确率 100%、选项分布正确。
- 教师发布填空题成功，学生提交标准答案后自动判对。

## 留待后续阶段

- 草稿自动保存和重登恢复属于 Q-IN-11，按实施方案列入后续增强。
- AI 简答反馈、加分计算、答案导出和即时大屏展示属于 P1/P2 增强。
- 下一阶段按实施方案进入“阶段 7：作业管理 P0”。
