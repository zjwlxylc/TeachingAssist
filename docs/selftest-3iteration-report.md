# 全模块四维度自检闭环报告（三迭代）

> 项目：大学教学过程辅助软件（TeachingAssist）
> 范围：认证/系统/备份/恢复、课前准备/课堂/公告/私信、问答/互动/作业/评估、AI 管理/聊天、前端 UI
> 四维：①错误检测 ②操作流程合理性 ③前端显示改进 ④后端数据库自检
> 方法：自检 → 规划 → 改进 → 测试，完整迭代 3 次，每次基于上一轮遗留问题深化
> 验证：隔离测试库（`.selftest`，`config/local.yaml` 覆盖 `storage.local_root`）+ `scripts/selftest_smoke.py`
> 结果：**后端冒烟 24/24 通过，前端 `tsc` + `vite build` 通过**

---

## 一、迭代总览

| 迭代 | 重点 | 核心产出 | 测试结果 |
|------|------|----------|----------|
| 迭代1 | 后端 4 模块 + 前端维度③ | 鉴权/备份/WS/AI/评估/作业 等 10+ 项修复；前端 AppSnackbar/状态重置/WS 重连/http 容错 | 15/15 |
| 迭代2 | 深化遗留（架构级） | 读路径写副作用→后台定时、AI 课堂超时预算、API Key Fernet 加密、学生私信会话令牌 | 22/22 |
| 迭代3 | 第三轮深层闭环 | 私信强制令牌、PII 读取令牌优先、GET 标记已读→POST、索引补全、Key 掩码、作业长度校验、切身份清空 | 24/24 |

---

## 二、迭代1 — 模块级修复（错误检测 + 流程 + 前端）

### 2.1 认证 / 系统 / 备份 / 恢复
- **High** `recovery.cached_replay` 缺教师鉴权 → 加 `Depends(require_teacher)`（`routes/recovery.py`）
- **Mid** 备份同秒覆盖 + 恢复无完整性校验 → `backup.py` 加 uuid 后缀、`_verify_sqlite_integrity()`、`os.replace` 原子替换
- **Mid** 自动备份阻塞事件循环 → `startup.auto_backup_worker` 改用 `run_in_executor`
- **Low** 访问地址不持久化 → `network.py` 新增 `save/load_selected_access()`，`system.py` 落库
- **Low** `auth._get_teacher` 含写副作用与乱码兼容分支 → 纯查询化

### 2.2 课前准备 / 课堂 / 公告 / 私信
- **Mid** WS 单卡 socket 拖垮整组 → `realtime.broadcast` 加 `SEND_TIMEOUT_SECONDS=5` 的 `wait_for`
- **Mid** WS 空闲无超时 → `announcements.py`/`messages.py` 加 `WS_IDLE_TIMEOUT_SECONDS=300` 空闲断开

### 2.3 问答 / 互动 / 作业 / 评估
- **High** AI 在事务内调用（SQLite 锁反模式）→ `interactions.publish_student_message` 重构为「只读→关连接→事务外调 AI→新连接写」三阶段
- **High** 作业重复批阅回退状态 → `start_ai_review` 筛选排除 `ai_reviewed/teacher_reviewed`
- **Mid** `allow_late` 永不归档 → `_refresh_homework_status` 截止后一律 `closed`
- **Mid** 填空 list 被 `str(list)` 污染 → `_grade_answer` 兼容 list/字符串
- **Mid** `calculate_session` N+1 → 一次性聚合，查询 1+4N → ~6

### 2.4 AI 管理 / 聊天
- **High** 结构化 JSON 被 `max_length` 截断致 `json.loads` 失败 → `generate_structured_json` 传 `truncate=False, replace_keywords=False`
- **Mid** 畸形响应 500 → `_post_chat_completion` 的 `json.loads` 移入 try 捕获 `JSONDecodeError`

### 2.5 前端（维度③）
- **High** `AppSnackbar` 背景色硬编码橙色致 severity 全失效 → 移除硬编码，由 MUI `filled` 变体按 severity 着色
- **High** 学生切换课堂 `result` 未重置 → 切换 `currentSession` 时 `setResult(null)`
- **Mid** `http.ts` 非 JSON 响应抛 `SyntaxError` → 改用 `text()` + 容错 `JSON.parse`
- **Mid** `websocket.ts` 无限重连 → 指数退避 + 最大重试 + 连接去重
- **Mid** `TeacherPage` 私信 WS/轮询随会话切换重建 → 解耦 `selectedMessageStudentPk` 依赖，用 ref 持有

### 迭代1 新增迁移 / 脚本
- `migrations/017_query_indexes.sql`：补 10 个高频查询索引
- `scripts/selftest_smoke.py`：可扩展冒烟脚本

---

## 三、迭代2 — 深化（架构级遗留）

| # | 问题 | 修复 | 严重度 |
|---|------|------|--------|
| A | `get_session_public`/`list_active_sessions` 读路径调 `refresh_session_statuses()` 写库+触发备份 | 状态刷新改为 `startup.session_status_worker` 后台每 60s 执行；两读接口纯读 | High |
| B | AI 课堂最多 3 次串行 AI 调用无整体预算 | `ai_chat.py` 分类器短超时 + `AI_CHAT_OVERALL_TIMEOUT_SECONDS=40` 总体守卫，超时优雅降级 | High |
| C | API Key 明文入库 | `cryptography` Fernet 加密（`enc::` 前缀 + 旧明文兼容）；`requirements.txt` 加依赖 | High |
| D | 学生私信仅靠学号+姓名，可冒名 | 迁移 `018_student_sessions.sql` + `services/student_auth.py`；签到发令牌；读/发/WS 强制令牌 | High |

验证：新增加密往返测试、学生令牌全链路（签到发令牌→带令牌发信/读会话→错误令牌 401）。

---

## 四、迭代3 — 第三轮深层闭环

| # | 问题 | 修复 | 严重度 |
|---|------|------|--------|
| 1 | 私信表单列缺索引 | `migrations/019_message_indexes.sql` | Low |
| 2 | `get_ai_overview` 的 `api_key_masked` 泄露首尾片段 | `_redact_secret` 改固定 `****` | Mid |
| 3 | 作业反馈/评估反馈/答题草稿仅靠学号+姓名，可越权读他人隐私 | 三处 service 加 `token` 参数：令牌优先（强制绑定本课堂），无令牌回退学号+姓名（供 AI 课堂服务端复用）；路由透传；前端带 `studentToken` | High |
| 4 | GET `/messages/mine` 内「标记已读」属于读路径写副作用 | 改为显式 `POST /messages/mine/read`；StudentPage/TeacherPage 打开会话时调用 | Mid |
| 5 | 学生切换身份未清空私信 state | 私信 effect 守卫内清空 `privateMessages` | Mid |
| 6 | 作业提交文本无长度上限 | 后端 `MAX_HOMEWORK_TEXT_LENGTH=5000` 校验；前端 TextField `maxLength` | Mid |
| 7 | 私信仍保留学号+姓名兜底（冒名风险残留） | 强制令牌：`messages.py`/`routes/messages.py` WS 移除学号+姓名兜底；前端 WS URL 仅传 token、守卫三者齐全才连接 | High |

验证：新增「带令牌读取草稿（令牌优先/防伪名）」「无令牌兜底（服务端兼容）」「错误令牌 401」等用例。

---

## 五、测试与质量门禁

- 隔离测试库：`config/local.yaml` → `storage.local_root: D:/Agent/TeachingAssist-main/.selftest`（不污染真实 `C:/TeachingAssist`）
- 后端：`PYTHONPATH=backend python -m compileall backend/app` 通过；`scripts/selftest_smoke.py` **24/24**
- 前端：`npx tsc --noEmit` 通过；`npm run build` 通过
- 迁移：017/018/019 均在初始化阶段 apply，冒烟测试已覆盖

---

## 六、遗留与说明（已接受的风险）

1. **PII 读取的学号+姓名兜底**：刻意保留供 AI 课堂服务端路径复用；学生端 HTTP 接口前端始终带令牌，常规使用已闭环。若需彻底杜绝「裸 API 调用凭学号姓名越权」，可在三个学生路由层再加「无 token 即 401」（AI 课堂走 service 不经过 HTTP 路由，不受影响）——留作后续可选增强。
2. **学生令牌刷新丢失**：令牌存于 React state，页面刷新后丢失（与私信 WS 行为一致）；课堂场景下一般不刷新，当前可接受。
3. **`.selftest/` 隔离库**：测试产物，已 gitignore，可随时清理。

---

## 七、交付文件清单（本轮新增/修改）

- 新增：`migrations/017_query_indexes.sql`、`018_student_sessions.sql`、`019_message_indexes.sql`、`services/student_auth.py`、`scripts/selftest_smoke.py`、`docs/selftest-3iteration-report.md`
- 修改：后端 21 个 py（routes/services/main/requirements）、前端 11 个 ts/tsx
- 收尾：删除 `config/local.yaml` 恢复真实 `C:/TeachingAssist` 存储配置
