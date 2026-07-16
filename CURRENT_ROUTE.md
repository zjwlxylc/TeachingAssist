# TeachingAssist Current Route

日期：2026-07-16
机器权威：`PROJECT_STATE.yaml`（single machine authority）

## 产品位置

- 实施方案阶段 1–10 已完成。
- 当前产品门禁保持为真实机房试点、教师/学生反馈收集和基于反馈的缺陷修复。
- 本次 ALE 适配不授权新的产品功能，不改变 React、API、SQLite、Provider、认证或部署行为。

## 当前控制面 Outcome

- Outcome：`ALE-TA-1` — ALE v1.5.0 TeachingAssist Adaptation。
- 状态：`in_progress`。
- 当前任务：建立协议、项目状态检查和确定性验证入口。
- 授权分支：`codex/ale-v1-5-adaptation`。
- 基线：`4ed88a90a07ff44383be17ade63eb4e677e053df`。

## Git 边界

- 当前分支允许精确提交。
- 未授权 push 工作分支。
- 未授权 merge `main` 或 push `origin/main`。
- 源项目只读，不得写入。

## 验收边界

- 自动验证尚未完成。
- 自动验证不等于人工验收。
- 最新验收包：`docs/ale_ta_1_manual_acceptance.md`。
- 只有用户作出 `accepted / repair_required / rejected` 决策后才能更新人工状态。

## 冷启动下一步

1. 读取 `PROJECT_STATE.yaml`。
2. 读取本文件和 `docs/ale_ta_1_manual_acceptance.md`。
3. 读取 `CODEX_WORKFLOW.md` 与 `docs/agentic_loop_engineering.md`。
4. 验证 Git 分支、HEAD 与保护引用。
5. 继续 ALE-TA-1；不得提前进入新的产品 Outcome。
