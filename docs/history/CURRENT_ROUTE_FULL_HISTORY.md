# TeachingAssist Route History

本文件保存 `CURRENT_ROUTE.md` 精简前的稳定路线事实和后续关闭记录。只追加已验证事实，
当前执行状态始终以 `PROJECT_STATE.yaml` 为准。

## 2026-07-16 — ALE-TA-1 启动前快照

- 大学教学过程辅助软件实施方案阶段 1–10 已交付。
- 已交付后端 FastAPI/SQLite、前端 React/Vite/TypeScript、课堂签到、公告、问答、作业、
  AI 降级与内容安全、P1 增强、打包部署和试点材料。
- 当前产品路线是目标机房真实试运行、教师和学生反馈整理、缺陷修复及体验优化。
- ALE-TA-1 仅建立开发控制面，不改变产品运行时、API、Schema、前端页面、Provider、
  认证权限或业务状态语义。
- ALE-TA-1 基线为 `4ed88a90a07ff44383be17ade63eb4e677e053df`，授权分支为
  `codex/ale-v1-5-adaptation`。
- 由于控制面尚未存在，本 Outcome 获得一次当前 checkout 引导例外；正式 worktree 规则在
  ALE-TA-1 被人工接受并进入主线后生效。
- 未授权 push、merge 主线或开始新的产品 Outcome。
