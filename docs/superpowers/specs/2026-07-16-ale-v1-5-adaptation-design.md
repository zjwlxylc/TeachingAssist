# ALE v1.5.0 项目适配设计

日期：2026-07-16
状态：已批准设计，等待书面规格复核
目标项目：大学教学过程辅助软件（TeachingAssist）
适配基线：`4ed88a90a07ff44383be17ade63eb4e677e053df`

## 1. 背景与决策

本项目已经具备 React、TypeScript、Vite、FastAPI、SQLite 和 WebSocket 运行架构，
不需要复刻源项目的 Vue 前端迁移。ALE v1.5.0 在本项目中的价值是建立开发控制面，
让任务能够按风险分级执行、从仓库恢复事实、保护主线、保留失败证据，并停在人工验收门。

源项目 `industrial-cognitive-system` 的 ALE 协议、状态文件、检查器、测试和
“用 ALEv1.5.0 重构前端并复盘”任务仅作为只读参考。适配不得修改源项目，
不得复制其工业设备、Phase、候选报告或业务状态语义。

采用“协议 + 项目状态 + 确定性执行工具”的方案。仅复制文档会缺少可执行约束；
完整照搬源仓库会引入无关治理负担。

## 2. 目标

- 在仓库内建立 ALE v1.5.0 单一权威协议。
- 提供 `Micro Fix Loop`、`Deterministic Fast Loop`、`Full ALE` 三种互斥模式。
- 用结构化状态记录当前路线、Git 权限、边界、验证和人工验收状态。
- 为未来 Codex 窗口提供短、稳定、可恢复的启动顺序。
- 提供项目级 `doctor`、`focused`、`exit` 验证入口。
- 失败时保留首次结果，并支持区分分支回归、基线失败和不稳定门禁。
- 保持“自动验证不等于人工验收”。

## 3. 非目标

- 不修改 React 页面、前端架构、API、SQLite Schema 或业务状态机。
- 不修改 Provider 行为、认证权限或部署运行方式。
- 不引入 Vue、Playwright、SSR、独立生产前端服务器或新产品功能。
- 不建立与 ALE 平行的第二套计划、验收或状态体系。
- 不把源项目的工业领域术语、P24/P25 路线或候选对象带入本项目。
- 不自动合并 `main`、推送 `origin/main`、删除分支或删除 worktree。

## 4. 权威文件与职责

### 4.1 `docs/agentic_loop_engineering.md`

ALE v1.5.0 的唯一协议正文，包含：

- 模式分类与升级条件；
- 最小用户契约；
- 冷启动事实恢复顺序；
- Full ALE 的 Scope Card、Journey Slice、RED/GREEN、修复预算；
- 正式工作分支与 worktree 约束；
- 停止、恢复、人工验收和接受后收口规则；
- 通用 Outcome 模板。

协议保持项目无关，仅在测试入口、Windows 环境和 TeachingAssist 边界处做项目适配。

### 4.2 `PROJECT_STATE.yaml`

使用 JSON 兼容 YAML，便于 Python 标准库无依赖解析。它是当前状态、Git 权限、边界和
下一门禁的唯一机器权威，但不保存绝对路径、解释器路径、运行日志或操作者信息。

初始状态表达：

- 阶段 1–10 已完成；
- 当前路线是机房试点、反馈收集和缺陷修复；
- ALE 适配 Outcome 为 `ALE-TA-1`；
- 产品运行时未因本 Outcome 改变；
- 合并和推送主线默认禁止，只有人工接受后再单独授权。

### 4.3 `CURRENT_ROUTE.md`

不超过 140 行的人类恢复指针，只说明当前产品位置、当前 ALE 门禁、边界、
最近验收包和推荐下一步，不重复机器字段或长期历史。

### 4.4 `CODEX_WORKFLOW.md`

记录本项目长期执行约定：一次任务一个当前 Outcome、启动读取顺序、精确暂存、
中文 Markdown 编码、React/FastAPI/SQLite 验证边界以及不自动进入下一阶段。

### 4.5 `AGENTS.md`

只新增简短入口：非平凡任务先读 `PROJECT_STATE.yaml`、`CURRENT_ROUTE.md` 和
`CODEX_WORKFLOW.md`；ALE Outcome 再读协议正文。不得在 `AGENTS.md` 重复协议细节。

## 5. 执行工具

### 5.1 `scripts/check_project_state.py`

使用 Python 标准库实现两类检查：

- Full ALE：状态结构、权威文件、路线一致性、Git 基线、受保护引用、当前分支和
  正式 worktree 身份；
- Deterministic Fast Loop：通过命令行传入基线、授权分支和精确文件列表，检查
  暂存、未暂存、已提交差异和 `git diff --check`，不读取持久状态。

检查器不得修改 Git、文件或环境。

### 5.2 `scripts/ale.py`

提供一个薄调度层，不复制业务测试逻辑：

- `doctor`：检查仓库身份、分支、Python 虚拟环境、必需导入、Node、npm、
  `frontend/node_modules`、隔离自检配置和状态检查器；
- `focused --target control-plane`：运行 ALE 控制面单元测试和状态检查；
- `focused --target backend`：运行后端编译与隔离自检；
- `focused --target frontend`：运行 TypeScript 与 Vite 生产构建；
- `exit`：按固定顺序运行控制面、后端、前端和 diff 检查；
- `provenance`：记录首次失败、当前分支结果、冻结基线结果和诊断复跑结果。

运行证据写入被 Git 忽略的 `.ale-runs/`。日志不得包含 API Key、令牌、密码、
请求头、数据库内容或学生个人信息。

## 6. 失败来源证明

失败记录至少包含：

- 时间、任务标识、命令和执行目录；
- 当前分支、HEAD、声明基线；
- 首次冷运行退出码和输出摘要；
- 相同命令的基线退出码；
- 一次诊断复跑结果；
- 分类：`branch_regression`、`baseline_failure`、`gate_unstable` 或 `unclassified`。

规则：

- 当前分支失败、冻结基线通过，分类为 `branch_regression`；
- 当前分支与冻结基线均失败，分类为 `baseline_failure`；
- 首次失败但原命令诊断复跑通过，分类为 `gate_unstable`；
- 证据不足时保持 `unclassified`，不得把红灯改写成绿色；
- 基线复现必须在独立 checkout/worktree 执行，不得切换或污染当前工作目录。

## 7. 三档模式的项目适配

### Micro Fix Loop

仅用于单模块文案、CSS、纯展示或极小局部修复。执行聚焦 RED/GREEN、必要语法检查和
`git diff --check`；不创建 Scope Card、状态文件或全量验收包。

### Deterministic Fast Loop

用于根因已知、目标明确、无 API/Schema/业务状态/依赖变化的单一生产模块修改。
最多两轮最小修复，使用瞬时允许文件列表，不修改 `PROJECT_STATE.yaml` 和路线文件。

### Full ALE

用于依赖、API、Schema、跨模块、复杂前端旅程、持久状态、跨窗口恢复或高风险边界。
必须建立 Scope Card、Journey Slices、真实 RED/GREEN、风险匹配验证和人工验收包。

## 8. 状态流与停止条件

Full ALE Outcome 状态流：

```text
in_progress
  -> awaiting_manual_acceptance
  -> accepted_closed
  -> acceptance_repair_required -> awaiting_manual_acceptance
  -> rejected_closed
```

以下情况立即停止：

- 需要跨越硬边界或新增权限；
- Git、状态、路线或验收包存在未解决冲突；
- 出现覆盖任务范围的意外改动；
- 同一 Loop 超过三轮最小修复仍失败；
- Fast Loop 需要 API、Schema、依赖、跨模块或完整回归；
- 需要合并、推送主线或删除 worktree，但没有明确授权。

失败时保留成功提交、失败差异、日志摘要和最小恢复动作，不 reset、不改写历史。

## 9. 验证策略

控制面采用真实 TDD：

1. 先创建失败测试，证明权威文件、模式、状态或检查器行为缺失；
2. 运行并记录 RED；
3. 最小实现协议、状态和工具；
4. 运行聚焦 GREEN；
5. 运行 `doctor`、三个 `focused` 目标和 `exit`；
6. 运行 `git diff --check`、敏感信息扫描和状态检查；
7. 生成 ALE-TA-1 人工验收包并停在人工门。

控制面测试使用 Python `unittest` 和临时 Git 仓库，不新增 pytest 依赖。业务验证复用现有：

- `.venv\\Scripts\\python.exe -m compileall backend\\app`
- `.venv\\Scripts\\python.exe scripts\\selftest_smoke.py`
- `npm.cmd run build`（目录 `frontend`）

## 10. Git 与引导例外

本次适配从干净且已同步的 `4ed88a9` 创建
`codex/ale-v1-5-adaptation` 分支。由于 ALE 控制面尚不存在，引导阶段允许在当前检出中
创建该分支；正式 worktree 规则在 ALE-TA-1 人工接受并进入主线后生效。

设计文档单独提交。后续实施按 Journey Slice 精确暂存和提交，不使用 `git add .`。
除非用户另行明确授权，不 push 适配分支、不合并 `main`、不推送 `origin/main`。

## 11. 验收标准

- 所有权威文件存在且互相引用一致。
- 状态检查器对合法状态返回 0，对非法状态、越界文件或受保护引用移动返回非 0。
- 三种模式互斥，Micro/Fast 不产生 Full ALE 持久治理产物。
- `doctor` 能明确报告环境缺失而不搜索整机、不自动安装依赖。
- `focused` 和 `exit` 使用项目现有命令，失败时返回原始非零退出码。
- failure provenance 不覆盖首次失败，不泄漏敏感信息。
- 后端编译、隔离自检 24/24、前端构建和控制面测试通过。
- 产品运行代码、API、Schema、React 页面、Provider 和业务状态语义无变更。
- 生成书面验收包后停在人工验收门。
