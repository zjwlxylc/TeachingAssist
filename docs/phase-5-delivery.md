# 阶段 5 交付说明

## 已完成

1. 建立课堂 WebSocket 通道：`/ws/classroom/{session_id}`。
2. 新增课堂公告表，公告采用先入库、后推送的模式。
3. 教师端支持选择课堂并发布 500 字以内公告。
4. 学生端进入课堂后可查看历史公告列表。
5. 学生端连接 WebSocket 后可实时接收教师公告。
6. 支持基于 `last_message_id` 的公告增量补拉，用于断线重连恢复。
7. 前端 WebSocket 客户端支持自动重连和关闭时停止重连。
8. Vite 开发代理已支持 `/ws` WebSocket 转发。

## 新增接口

```text
GET  /api/v1/announcements/sessions/{session_id}
GET  /api/v1/announcements/sessions/{session_id}?last_message_id={id}
POST /api/v1/announcements/sessions/{session_id}
WS   /ws/classroom/{session_id}
```

教师发布公告接口需要 Bearer Token；学生公告查看和 WebSocket 连接面向课堂局域网访问。

## 数据库变更

新增迁移：`backend/app/db/migrations/005_announcements_websocket.sql`

- `announcements`：保存课堂公告、发送者角色、发送者名称、置顶/删除标记和创建时间。

## 验证记录

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成 API/WebSocket 烟测：

- 创建课程、班级、课堂并导入学生。
- 启动课堂后建立 `/ws/classroom/{session_id}` 连接。
- 教师发布公告成功。
- WebSocket 客户端收到 `announcement.created` 消息。
- 历史公告列表可查询。
- 使用 `last_message_id` 可补拉增量公告。
- 超过 500 字公告由参数校验拦截。

## 留待后续阶段

- 公告置顶、删除、屏蔽属于 P1 公告管理增强。
- 学生发布公告、学生私信教师属于 P2。
- 问题发布、学生答题和统计将在阶段 6 接入同一实时通道。
