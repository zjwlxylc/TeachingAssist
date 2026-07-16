# TeachingAssist Current Route

日期：2026-07-16
机器权威：`PROJECT_STATE.yaml`（single machine authority）

## 产品位置

- 实施方案阶段 1–10 已完成。
- 当前产品门禁保持为真实机房试点、教师/学生反馈收集和基于反馈的缺陷修复。
- ALE-TA-1 本身不授权新的产品功能；并行教师默认密码改动由用户单独授权合入主线。

## 当前控制面 Outcome

- Outcome：`ALE-TA-1` — ALE v1.5.0 TeachingAssist Adaptation。
- 状态：`accepted_closed`。
- 当前任务：完成已授权的 `origin/main` 推送，不启动新的产品 Outcome。
- 授权分支：`main`。
- 基线：`4ed88a90a07ff44383be17ade63eb4e677e053df`。

## Git 边界

- 用户已明确验收 ALE-TA-1，并授权将 ALE 与教师默认密码提交合并到 `main`。
- 允许精确提交最终集成修正并 push `origin/main`。
- 不单独 push 工作分支。
- 源项目只读，不得写入。

## 验收边界

- 合并主线后的 ALE 退出门已通过：控制面 31/31、后端自检 24/24、前端构建成功。
- 教师默认密码专项与自检回归 6/6 通过。
- 已知非阻断项：Vite 主 chunk 606.18 kB，保留既有体积警告。
- 自动验证不等于人工验收。
- 最新验收包：`docs/ale_ta_1_manual_acceptance.md`。
- 用户人工决定：`accepted`。
- 教师默认密码提交与 ALE 验收范围分离，但已获用户主线集成授权。

## 冷启动下一步

1. 读取 `PROJECT_STATE.yaml` 和本文件。
2. 读取 `docs/ale_ta_1_manual_acceptance.md`。
3. 继续真实机房试点、反馈收集和缺陷修复。
4. 不得把 ALE-TA-1 的关闭解释为自动授权新的产品 Outcome。
