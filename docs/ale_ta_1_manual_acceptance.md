# ALE-TA-1 Manual Acceptance Package

outcome_batch: ALE-TA-1
status: accepted_closed
manual_acceptance: accepted
as_of: 2026-07-16

## Outcome

为 TeachingAssist 适配 ALE v1.5.0 开发控制面，使后续任务可按风险分级、从仓库恢复事实、
保护 Git 主线、运行确定性验证并保留失败来源证据。

## Hard boundaries and integration scope

- ALE-TA-1 本身不修改产品运行代码、React 页面、API、SQLite Schema、Provider、认证或部署行为。
- 源项目及其 ALE 内容只读。
- 用户已明确授权把 ALE 与并行教师默认密码提交合入 `main` 并 push `origin/main`。
- 不把自动验证解释为人工接受。

## Unified main integration

- ALE 适配原始提交与教师默认密码原始提交均通过 `codex/ale-v1-5-adaptation` 快进进入本地主线。
- 教师密码文档提交：`c062b3a / 658b5c1`。
- 教师密码代码提交：`b4c1958 / 891e225 / 8a6cd2c`。
- 这些产品提交不属于 ALE-TA-1 的人工验收证据范围，但用户已明确作出 `main integration authorized` 决定。
- 最终集成只修正自检对配置默认密码的读取，不改变教师密码产品语义。

## Acceptance evidence

- 设计规格已确认：`docs/superpowers/specs/2026-07-16-ale-v1-5-adaptation-design.md`。
- 详细计划已提交：`docs/superpowers/plans/2026-07-16-ale-v1-5-adaptation.md`。
- 隔离 ALE 最终分支退出门已通过：控制面 29/29、后端自检 24/24、前端生产构建成功。
- 合并主线后的 `python scripts/ale.py exit` 已通过：控制面 31/31、后端自检 24/24、前端生产构建成功、`git diff --check` 通过。
- 教师默认密码专项与自检回归 6/6 通过。
- 主线项目状态检查返回 `passed: true`。
- 已知非阻断项：Vite 主 chunk 606.18 kB，保留既有体积警告。

Automated verification does not equal human acceptance.

## Human checks completed

1. 从 `PROJECT_STATE.yaml` 和 `CURRENT_ROUTE.md` 能否恢复唯一当前路线；
2. 三种执行模式是否互斥且升级条件明确；
3. `doctor/focused/exit` 是否复用仓库现有验证；
4. 失败来源证明是否保留首次失败并完成脱敏；
5. 产品代码和运行行为是否保持不变。

## Human decision

当前决定：`accepted`。

用户随后明确要求将 ALE 与教师默认密码改动全部合并到主线并推送；该授权不自动开始新的产品 Outcome。
