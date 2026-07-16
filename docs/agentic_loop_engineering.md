# Agentic Loop Engineering (ALE) v1.5.0

本文是本仓库使用的 ALE v1.5.0 唯一协议正文。它约束开发代理如何选择执行模式、恢复事实、
保护 Git 主线、运行验证、保存失败证据并停在人工验收门。项目状态以仓库文件为准，聊天内容
只作为输入，不是事实权威。

Automated verification does not equal human acceptance.

## 1. Core invariants

- ALE has three mutually exclusive execution modes: `Micro Fix Loop`,
  `Deterministic Fast Loop`, and `Full ALE`.
- 一个任务在同一时刻只能属于一种模式；条件变化时必须显式升级，不能混用门禁。
- Git、仓库文档和可复现命令是事实来源；不得用会话记忆覆盖仓库事实。
- 自动化可以证明已执行的检查，不得替代人工业务判断。
- 未获明确授权，不得 merge `main`、push `origin/main`、删除分支或删除 worktree。
- 首次失败必须保留；诊断复跑通过不能把首次红灯改写成绿色。
- Full ALE 的单个 Loop 只允许 a maximum of three minimal self-repair rounds。

## 2. Mode selection

### 2.1 Micro Fix Loop

仅适用于影响单一局部、无需跨模块推理的文案、CSS、纯展示或同等规模修复，同时满足：

- 不改变 API、Schema、持久状态、依赖、认证、Provider 或部署方式；
- 不需要跨窗口恢复；
- 一个聚焦测试或等价语法检查足以覆盖风险；
- 没有未知根因。

执行最小 RED/GREEN、必要语法检查和 `git diff --check`。该模式不得创建或修改
`PROJECT_STATE.yaml`、`CURRENT_ROUTE.md` 或 Full ALE 验收包。

### 2.2 Deterministic Fast Loop

仅适用于根因已知、目标明确、授权文件集合精确且不跨越高风险边界的单一生产模块修改。
它必须声明冻结基线、授权工作分支、允许文件列表、聚焦验证和退出检查；最多两轮最小修复。

Fast Loop 的允许文件列表只存在于本次命令输入中，不写入持久状态。任何 tracked、staged、
committed 或 untracked 越界文件都会使门禁失败。

### 2.3 Full ALE

以下任一条件成立时必须使用 Full ALE：

- 依赖、API、数据库 Schema、认证、Provider 或部署边界变化；
- 跨模块行为或复杂用户旅程变化；
- 需要跨窗口恢复或持久状态；
- 根因不确定、风险较高或需要完整回归；
- Fast Loop 发现范围扩大或无法在两轮内收敛。

Full ALE 必须维护 Scope Card、Journey Slices、真实 RED/GREEN、风险匹配验证、失败证据、
书面验收包和人工决策门。

## 3. Minimum user contract

开始非平凡工作前，必须从用户输入和仓库事实中得到五项输入：

1. `Outcome`：要得到的可观察结果；
2. `Acceptance`：什么证据足以交给人工判断；
3. `Hard boundaries`：禁止触碰的文件、行为和外部系统；
4. `Git authority`：允许创建、提交、推送或合并哪些引用；
5. `Stop condition`：何时必须停止并向用户交接。

缺失信息可从仓库稳定事实安全推导时，应明确记录假设；会改变范围或权限时必须停止询问。

## 4. Cold-start fact recovery

Full ALE 冷启动按以下顺序恢复：

1. 读取 `AGENTS.md` 和更深层适用的代理指令；
2. 读取 `PROJECT_STATE.yaml`，把它作为 single machine authority；
3. 读取 `CURRENT_ROUTE.md` 和其中指向的最新验收包；
4. 读取 `CODEX_WORKFLOW.md` 与本协议；
5. 用 Git 验证根目录、当前分支、HEAD、基线、保护引用和工作树；
6. 读取本 Outcome 的计划、测试入口和必要业务文档；
7. 运行 `python scripts/ale.py doctor`，再开始修改。

如果状态、路线、Git 或验收包互相冲突，停止执行并报告冲突，不猜测哪个版本正确。

## 5. Scope Card

Full ALE 在写生产实现前建立一张不超过八项的 Scope Card：

- Outcome ID 与名称；
- 用户可观察结果；
- In scope；
- Out of scope；
- 允许文件与禁止边界；
- 基线与授权工作分支；
- 验证命令；
- 人工验收与停止条件。

每一项必须可验证。不能写“顺便优化”“相关文件”等开放式范围。

## 6. Git and worktree discipline

- 开始前记录 baseline branch、baseline commit、authorized work branch。
- `main` 和 `origin/main` 是受保护引用；未授权时必须保持在声明基线。
- 正式 Full ALE 应在独立 worktree 中执行，且分支只能被该 worktree 持有。
- 新 worktree 必须复用已验证运行环境，不能静默创建另一套依赖事实。
- 只暂存本 Journey Slice 的明确文件，不使用 `git add .`。
- 不 reset、不改写历史、不用切换主工作目录的方式复现基线。
- 本仓库 ALE-TA-1 是控制面尚不存在时的引导例外；例外只适用于
  `in_progress` 或 `awaiting_manual_acceptance`，人工关闭后失效。

## 7. Runtime environment

- Python 使用仓库 `.venv/Scripts/python.exe`；不得自动安装或搜索整机解释器。
- 前端使用仓库现有 `frontend/node_modules` 和锁定版本；不得无故升级 Node/Vite/MUI。
- 本机覆盖配置只放 `config/local.yaml`，不得提交绝对路径、密钥或个人信息。
- 隔离自检数据只写入被忽略的项目目录，不能依赖教师机真实数据库。
- 环境不满足时，`doctor` 输出一个可操作错误并停止。

## 8. Journey Slice loop

每个 Full ALE Journey Slice 都按相同闭环执行：

1. 写一个能表达缺失行为的最小测试或契约断言；
2. 运行测试，确认它因目标能力缺失而 RED；
3. 写通过该测试所需的最小实现；
4. 运行聚焦测试确认 GREEN；
5. 运行与风险匹配的相邻回归；
6. 检查 diff、范围和敏感信息；
7. 精确暂存并提交；
8. 更新可恢复状态或进入下一个 Slice。

测试错误、环境错误和预期行为失败必须区分。若 RED 不是因为目标能力缺失，先修正测试环境。

## 9. Repair budget

- Full ALE 每个 Loop 最多三轮最小自修复；Fast Loop 最多两轮。
- 一轮只处理一个已证明根因，不得借修复扩大功能。
- 同一门禁超过预算仍失败时立即停止，保留失败 diff、命令、退出码和恢复建议。
- 基线也失败时，不把基线问题伪装为本分支回归；是否扩大修复范围由人工决定。

## 10. Failure provenance

首次失败证据至少记录：UTC 时间、任务 ID、命令、执行目录、当前分支、HEAD、声明基线、
首次退出码与脱敏摘要、冻结基线退出码、一次诊断复跑退出码和分类。

分类规则：

- 当前分支失败且冻结基线通过：`branch_regression`；
- 当前分支和冻结基线均失败：`baseline_failure`；
- 首次失败但诊断复跑通过：`gate_unstable`；
- 证据不足：`unclassified`。

冻结基线只能在独立 checkout/worktree 复现。证据写入 `.ale-runs/`，必须过滤 API Key、
令牌、密码、Authorization 请求头、数据库内容和学生个人信息。

## 11. Verification gates

验证强度匹配风险：

- Micro：聚焦测试或语法检查，加 `git diff --check`；
- Fast：声明文件的聚焦测试、范围检查、必要编译，加 `git diff --check`；
- Full：`doctor`、控制面、后端、前端、状态一致性和 `exit` 全部门禁。

TeachingAssist 的仓库级入口是：

```powershell
.\.venv\Scripts\python.exe scripts\ale.py doctor
.\.venv\Scripts\python.exe scripts\ale.py focused --target control-plane
.\.venv\Scripts\python.exe scripts\ale.py focused --target backend
.\.venv\Scripts\python.exe scripts\ale.py focused --target frontend
.\.venv\Scripts\python.exe scripts\ale.py exit
```

`exit` 的通过只表示技术证据齐备，状态必须进入 `awaiting_manual_acceptance`，不能自动关闭。

## 12. Stop and resume

出现以下任一情况立即停止：

- 需要越过硬边界、扩大文件范围或获得新权限；
- Git、状态、路线、计划或验收包存在未解决冲突；
- 发现覆盖任务范围的意外用户改动；
- 超过修复预算；
- 需要 merge、push 主线或删除 worktree，但未获授权；
- 验证证据无法安全脱敏。

停止时保留已通过的提交、未通过的最小差异、首次失败证据、当前状态和下一条可执行命令。
恢复时重新执行冷启动顺序，不依赖旧会话记忆。

## 13. Human acceptance

Full ALE 的自动验证完成后，生成书面验收包并将状态设为
`awaiting_manual_acceptance` / `pending`。人工决策只有：

- `accepted`：用户确认结果，可另行授权收口；
- `repair_required`：记录具体差距，回到最小修复 Loop；
- `rejected`：记录原因并关闭 Outcome，不合并未接受结果。

代理不得代替用户选择，也不得把沉默当作接受。

## 14. Post-acceptance closeout

只有收到明确接受及相应 Git 授权后，才能：更新为关闭状态、执行最终回归、推送工作分支、
创建或合并 PR、推送主线、清理分支/worktree。每一种外部写入都服从用户实际授权范围。
产品下一 Outcome 需要新的用户契约，不因本 Outcome 接受而自动开始。

## 15. Outcome template

```text
Outcome ID:
Name:
Mode:
Observable result:
In scope:
Out of scope:
Allowed files:
Hard boundaries:
Baseline commit:
Authorized work branch:
Acceptance evidence:
Human decision: pending
Stop condition:
```
