# 阶段 2 交付说明

## 已完成

1. 教师首次设置密码接口与前端表单。
2. 教师登录、退出登录、当前教师信息接口。
3. 密码 PBKDF2-SHA256 加盐哈希存储，未保存明文密码。
4. 连续 5 次登录失败后锁定 5 分钟。
5. 教师端系统管理接口已接入 Bearer Token 鉴权。
6. 本机局域网 IPv4 候选地址枚举，自动过滤回环地址并优先选择私有地址。
7. 默认端口与备选端口检测，生成课堂访问地址。
8. Windows 防火墙规则状态探测与管理员 `netsh` 引导命令。
9. 本地与可移动盘备份目标初始化。
10. 手动备份接口与教师端按钮。
11. 自动备份后台任务，每 15 分钟执行一次。
12. 备份保留最近 5 份，备份记录写入数据库。
13. 从备份恢复接口，恢复前自动生成 `before_restore_*.db` 安全副本。
14. 教师端页面展示启动检查、访问地址、防火墙引导和备份记录。

## 新增接口

```text
GET  /api/v1/auth/status
POST /api/v1/auth/setup
POST /api/v1/auth/login
POST /api/v1/auth/logout
GET  /api/v1/auth/me

GET  /api/v1/system/access
POST /api/v1/system/access
GET  /api/v1/system/backups
POST /api/v1/system/backups
POST /api/v1/system/backups/restore
```

除 `/auth/status`、`/auth/setup`、`/auth/login` 和 `/system/startup` 外，教师端系统管理接口需要 `Authorization: Bearer <token>`。

## 数据库变更

新增迁移：`backend/app/db/migrations/002_system_management.sql`

- `auth_tokens`：教师登录令牌。
- `backup_records`：备份执行记录。
- `network_settings`：后续保存网卡与端口偏好的预留表。
- 默认教师记录：`teachers.id = 1`。

## 验证记录

已执行：

```powershell
.\.venv\Scripts\python.exe -m compileall backend\app
$env:PYTHONPATH = (Resolve-Path backend).Path
.\.venv\Scripts\python.exe scripts\init_db.py
cd frontend
npm.cmd run build
```

已完成本地 API 烟测：

- 后端可在 `127.0.0.1:8090` 启动。
- `/api/v1/auth/status` 可读取密码设置状态。
- 首次设置密码或使用测试密码登录成功。
- `/api/v1/auth/me` 可在 Bearer Token 下返回当前教师。
- `/api/v1/system/access` 可返回候选 IP、访问 URL 和防火墙引导。
- `/api/v1/system/backups` 可创建本地与可移动盘备份，记录状态为 `success`。

注意：当前 PowerShell 终端在直接打印中文 JSON 时可能出现显示乱码，源码、Markdown 与 HTTP 响应均按 UTF-8 保存。

## 留待后续阶段

- 课堂结束后的强制课后备份将在课堂生命周期阶段接入。
- 完整教学数据 Excel/CSV/JSON 导出将在数据统计与验收阶段补齐。
- 网卡/端口选择持久化可在系统设置增强阶段继续完善。
- 备份恢复接口已完成后端能力，前端恢复选择器可在后续设置页细化。
