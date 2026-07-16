# ALE v1.5.0 TeachingAssist Adaptation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变任何产品运行行为的前提下，为 TeachingAssist 建立可执行、可恢复、可人工验收的 ALE v1.5.0 开发控制面。

**Architecture:** 以仓库内协议、JSON 兼容 YAML 状态和精简路线文件构成持久控制面；以 Python 标准库实现只读状态检查器和 `doctor/focused/exit/provenance` 薄调度入口。业务验证继续调用现有后端编译、自检脚本和前端构建，不复制业务测试逻辑。

**Tech Stack:** Python 3.13 标准库、`unittest`、Git CLI、PowerShell/Windows、React 18、TypeScript 5.4、Vite 4、FastAPI、SQLite。

## Global Constraints

- 源项目 `industrial-cognitive-system` 及其 ALE 文件只读，禁止写入。
- 适配协议版本固定为 `ALE v1.5.0`，不得发明 `v1.6.0`。
- 实施基线固定为 `4ed88a90a07ff44383be17ade63eb4e677e053df`。
- 授权工作分支固定为 `codex/ale-v1-5-adaptation`。
- 不修改 React 页面、业务 API、SQLite Schema、Provider、认证权限或业务状态语义。
- 不引入 Vue、Playwright、SSR、独立生产前端服务器或产品功能。
- 控制面运行证据只能写入被忽略的 `.ale-runs/`，不得记录密钥、令牌、密码、数据库内容或学生个人信息。
- 所有行为和契约变更执行真实 `RED -> minimal change -> GREEN`。
- 每次只暂存明确列出的文件，不使用 `git add .`。
- 允许提交当前工作分支；未经额外授权，不 push、不 merge `main`、不 push `origin/main`。

## File Map

- `docs/agentic_loop_engineering.md`：ALE v1.5.0 唯一协议正文。
- `PROJECT_STATE.yaml`：状态、Git 权限、边界、验证和下一门禁的机器权威。
- `CURRENT_ROUTE.md`：不超过 140 行的人类恢复指针。
- `CODEX_WORKFLOW.md`：TeachingAssist 长期执行约定。
- `docs/history/CURRENT_ROUTE_FULL_HISTORY.md`：适配前路线快照与后续追加历史。
- `docs/ale_ta_1_manual_acceptance.md`：ALE-TA-1 人工验收包。
- `AGENTS.md`：只增加 ALE 权威入口，不复制协议细节。
- `scripts/check_project_state.py`：Full ALE 与 Fast Loop 的只读一致性检查器。
- `scripts/ale.py`：`doctor/focused/exit/provenance` 命令入口。
- `backend/requirements-dev.txt`：复现自检所需的开发依赖入口。
- `.gitignore`：忽略 `.ale-runs/`。
- `tests/test_ale_protocol.py`：协议、权威文件和项目边界契约。
- `tests/test_ale_project_state_checker.py`：状态检查器行为测试。
- `tests/test_ale_cli.py`：验证入口与失败来源证明测试。

---

### Task 1: 建立 ALE 协议与仓库权威文件

**Files:**
- Create: `docs/agentic_loop_engineering.md`
- Create: `PROJECT_STATE.yaml`
- Create: `CURRENT_ROUTE.md`
- Create: `CODEX_WORKFLOW.md`
- Create: `docs/history/CURRENT_ROUTE_FULL_HISTORY.md`
- Create: `docs/ale_ta_1_manual_acceptance.md`
- Modify: `AGENTS.md`
- Test: `tests/test_ale_protocol.py`

**Interfaces:**
- Consumes: 已确认设计 `docs/superpowers/specs/2026-07-16-ale-v1-5-adaptation-design.md`。
- Produces: `PROJECT_STATE.yaml` 中固定字段 `schema_version`、`project`、`ale_protocol_version`、`authority`、`git`、`product_route`、`control_plane`、`boundaries`、`verification`，供 Task 2 检查器读取。

- [ ] **Step 1: 写协议与权威文件缺失的失败测试**

创建 `tests/test_ale_protocol.py`：

```python
from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AleProtocolContractTests(unittest.TestCase):
    def test_authoritative_files_exist(self) -> None:
        for relative in (
            "docs/agentic_loop_engineering.md",
            "PROJECT_STATE.yaml",
            "CURRENT_ROUTE.md",
            "CODEX_WORKFLOW.md",
            "docs/history/CURRENT_ROUTE_FULL_HISTORY.md",
            "docs/ale_ta_1_manual_acceptance.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_protocol_defines_three_mutually_exclusive_modes(self) -> None:
        text = (ROOT / "docs/agentic_loop_engineering.md").read_text(encoding="utf-8")
        for term in (
            "ALE v1.5.0",
            "three mutually exclusive execution modes",
            "Micro Fix Loop",
            "Deterministic Fast Loop",
            "Full ALE",
            "Automated verification does not equal human acceptance.",
            "maximum of three minimal self-repair rounds",
        ):
            self.assertIn(term, text)

    def test_state_is_json_compatible_yaml_for_teaching_assist(self) -> None:
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["schema_version"], 1)
        self.assertEqual(state["project"], "TeachingAssist")
        self.assertEqual(state["ale_protocol_version"], "1.5.0")
        self.assertEqual(
            state["git"]["baseline_commit"],
            "4ed88a90a07ff44383be17ade63eb4e677e053df",
        )
        self.assertEqual(
            state["git"]["authorized_work_branch"],
            "codex/ale-v1-5-adaptation",
        )
        self.assertFalse(state["git"]["merge_main_allowed"])
        self.assertFalse(state["git"]["push_origin_main_allowed"])

    def test_route_is_compact_and_points_to_machine_authority(self) -> None:
        text = (ROOT / "CURRENT_ROUTE.md").read_text(encoding="utf-8")
        self.assertLessEqual(len(text.splitlines()), 140)
        self.assertIn("PROJECT_STATE.yaml", text)
        self.assertIn("single machine authority", text)
        self.assertIn("真实机房试点", text)

    def test_source_project_business_terms_are_not_imported(self) -> None:
        combined = "\n".join(
            (ROOT / path).read_text(encoding="utf-8")
            for path in (
                "docs/agentic_loop_engineering.md",
                "PROJECT_STATE.yaml",
                "CURRENT_ROUTE.md",
                "CODEX_WORKFLOW.md",
            )
        )
        for forbidden in ("P23.R3", "P24", "candidate report", "CNC-01"):
            self.assertNotIn(forbidden, combined)

    def test_agents_contains_only_compact_ale_entry(self) -> None:
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("docs/agentic_loop_engineering.md", text)
        self.assertIn("PROJECT_STATE.yaml", text)
        self.assertIn("CURRENT_ROUTE.md", text)
        self.assertLess(text.count("Micro Fix Loop"), 2)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_protocol -v
```

Expected: `FAIL`，首个失败为 `docs/agentic_loop_engineering.md` 或其他权威文件不存在。

- [ ] **Step 3: 最小实现协议与状态文件**

`PROJECT_STATE.yaml` 初始内容必须采用以下字段和值；`authority` 中的每个路径都必须在本任务创建：

```json
{
  "schema_version": 1,
  "as_of": "2026-07-16",
  "project": "TeachingAssist",
  "ale_protocol_version": "1.5.0",
  "authority": {
    "current_route": "CURRENT_ROUTE.md",
    "latest_handoff": "docs/ale_ta_1_manual_acceptance.md",
    "route_history": "docs/history/CURRENT_ROUTE_FULL_HISTORY.md",
    "manual_acceptance_package": "docs/ale_ta_1_manual_acceptance.md"
  },
  "git": {
    "baseline_branch": "main",
    "baseline_commit": "4ed88a90a07ff44383be17ade63eb4e677e053df",
    "authorized_work_branch": "codex/ale-v1-5-adaptation",
    "push_work_branch_allowed": false,
    "merge_main_allowed": false,
    "push_origin_main_allowed": false
  },
  "product_route": {
    "completed_stage": 10,
    "current_gate": "real_classroom_pilot_and_feedback",
    "next_product_work_authorized": false
  },
  "control_plane": {
    "outcome_batch": "ALE-TA-1",
    "name": "ALE v1.5.0 TeachingAssist Adaptation",
    "status": "in_progress",
    "manual_acceptance": "not_performed",
    "bootstrap_in_place_allowed": true,
    "follow_up_gate": "human_acceptance_required"
  },
  "boundaries": {
    "runtime_changed": false,
    "api_changed": false,
    "frontend_changed": false,
    "storage_changed": false,
    "provider_changed": false,
    "authentication_changed": false,
    "new_product_feature_allowed": false
  },
  "verification": {
    "technical_verification": "not_run",
    "focused_control_plane": "not_run",
    "backend_verification": "not_run",
    "frontend_verification": "not_run",
    "automated_tests_equal_human_acceptance": false
  }
}
```

`docs/agentic_loop_engineering.md` 必须包含设计第 2、6、7、8、9、10 节定义的全部规则；
`CURRENT_ROUTE.md` 只记录阶段 10 完成、试点路线、ALE-TA-1 当前门和人工验收边界；
`CODEX_WORKFLOW.md` 记录启动读取顺序和 TeachingAssist 验证命令；
`docs/ale_ta_1_manual_acceptance.md` 明确当前为 `in_progress`，自动验证尚未执行，
并包含原句 `Automated verification does not equal human acceptance.`；
`AGENTS.md` 只增加一个不超过 20 行的 ALE 入口段落。

- [ ] **Step 4: 运行协议测试并确认 GREEN**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_protocol -v
```

Expected: 所有 `AleProtocolContractTests` 通过，退出码 `0`。

- [ ] **Step 5: 检查并提交 Task 1**

Run:

```powershell
git diff --check
git status --short
git add -- AGENTS.md CODEX_WORKFLOW.md CURRENT_ROUTE.md PROJECT_STATE.yaml docs/agentic_loop_engineering.md docs/history/CURRENT_ROUTE_FULL_HISTORY.md docs/ale_ta_1_manual_acceptance.md tests/test_ale_protocol.py
git diff --cached --check
git commit -m "docs(ale): 建立 TeachingAssist ALE v1.5.0 控制面"
```

Expected: 提交只包含上列 8 个文件。

---

### Task 2: 实现 Full ALE 与 Fast Loop 状态检查器

**Files:**
- Create: `scripts/check_project_state.py`
- Test: `tests/test_ale_project_state_checker.py`

**Interfaces:**
- Consumes: Task 1 的 `PROJECT_STATE.yaml` 固定结构。
- Produces: `build_full_report(project_root: Path) -> dict[str, object]`、`build_fast_report(project_root: Path, baseline_commit: str, authorized_work_branch: str, allowed_files: list[str]) -> dict[str, object]` 和 CLI 退出码，供 Task 3 调用。

- [ ] **Step 1: 写检查器失败测试**

创建 `tests/test_ale_project_state_checker.py`，至少包含：

```python
from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / "scripts/check_project_state.py"


def load_checker():
    spec = importlib.util.spec_from_file_location("check_project_state", CHECKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AleProjectStateCheckerTests(unittest.TestCase):
    def test_repository_state_passes(self) -> None:
        report = load_checker().build_full_report(ROOT)
        self.assertTrue(report["passed"], report["failures"])

    def test_machine_local_state_keys_are_rejected(self) -> None:
        module = load_checker()
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        state["runtime_identity"] = {"python_path": "C:/private/python.exe"}
        failures = module.check_state_schema(state)
        self.assertTrue(any("machine-local" in item for item in failures))

    def test_fast_report_rejects_out_of_scope_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "ale@example.invalid"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "ALE Test"], cwd=repo, check=True)
            (repo / "allowed.txt").write_text("base\n", encoding="utf-8")
            (repo / "outside.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "add", "allowed.txt", "outside.txt"], cwd=repo, check=True)
            subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True)
            baseline = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
                capture_output=True, text=True, encoding="utf-8"
            ).stdout.strip()
            subprocess.run(["git", "update-ref", "refs/remotes/origin/main", baseline], cwd=repo, check=True)
            subprocess.run(["git", "switch", "-c", "codex/fast-test"], cwd=repo, check=True)
            (repo / "outside.txt").write_text("changed\n", encoding="utf-8")
            report = load_checker().build_fast_report(
                repo, baseline, "codex/fast-test", ["allowed.txt"]
            )
            self.assertFalse(report["passed"])
            self.assertTrue(any("outside.txt" in item for item in report["failures"]))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_project_state_checker -v
```

Expected: `FAIL`，原因是 `scripts/check_project_state.py` 不存在。

- [ ] **Step 3: 实现无依赖只读检查器**

`scripts/check_project_state.py` 必须定义以下常量：

```python
STATE_FILE = "PROJECT_STATE.yaml"
FULL_ALE_MODE = "full_ale"
FAST_LOOP_MODE = "deterministic_fast_loop"
FORBIDDEN_MACHINE_LOCAL_KEYS = {
    "worktree_root", "worktree_path", "git_common_dir", "runtime_head",
    "python_path", "node_path", "operator_identity", "runtime_identity",
}
```

公开接口固定为：

- `load_state(path: Path) -> dict[str, object]`
- `check_state_schema(state: dict[str, object]) -> list[str]`
- `check_authority_paths(state: dict[str, object], project_root: Path) -> list[str]`
- `check_document_consistency(state: dict[str, object], project_root: Path) -> list[str]`
- `check_git_consistency(state: dict[str, object], git_root: Path) -> list[str]`
- `check_worktree_consistency(state: dict[str, object], git_root: Path) -> list[str]`
- `build_full_report(project_root: Path) -> dict[str, object]`
- `build_fast_report(project_root: Path, baseline_commit: str, authorized_work_branch: str, allowed_files: list[str]) -> dict[str, object]`
- `main(argv: list[str] | None = None) -> int`

实现要求：

- 所有 Git 命令使用 `git -c core.quotepath=false`、`encoding="utf-8"`。
- Full report 验证状态结构、权威路径、路线不超过 140 行、人工状态映射、基线祖先关系、
  `main/origin/main` 保护和 worktree 身份。
- `bootstrap_in_place_allowed` 只允许 `ALE-TA-1` 在 `in_progress` 或
  `awaiting_manual_acceptance` 状态使用；其他 Outcome 或关闭状态使用该字段必须失败。
- Fast report 不读取 `PROJECT_STATE.yaml`，只允许精确仓库相对路径；拒绝 `..`、绝对路径、
  越界 tracked/staged/committed diff 和重叠 untracked 文件。
- CLI 默认为 Full ALE；Fast Loop 必须同时提供 `--baseline-commit`、
  `--authorized-work-branch` 和至少一个 `--allowed-file`。
- `--format json` 输出 `ensure_ascii=False` 的稳定 JSON；失败退出 `1`，成功退出 `0`。

- [ ] **Step 4: 运行检查器测试与真实状态检查**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_project_state_checker -v
.\.venv\Scripts\python.exe scripts\check_project_state.py --format json
```

Expected: 单元测试全部通过；JSON 中 `"passed": true`。

- [ ] **Step 5: 提交 Task 2**

Run:

```powershell
git diff --check
git add -- scripts/check_project_state.py tests/test_ale_project_state_checker.py
git diff --cached --check
git commit -m "feat(ale): 增加项目状态一致性检查器"
```

Expected: 提交只包含检查器和对应测试。

---

### Task 3: 实现 doctor、focused 与 exit 验证入口

**Files:**
- Create: `scripts/ale.py`
- Create: `backend/requirements-dev.txt`
- Modify: `.gitignore`
- Test: `tests/test_ale_cli.py`

**Interfaces:**
- Consumes: Task 2 的 `scripts/check_project_state.py --format json`。
- Produces: `doctor(root: Path) -> int`、`focused(root: Path, target: str) -> int`、`exit_gate(root: Path) -> int`，供命令行和 Task 4 provenance 复用。

- [ ] **Step 1: 写验证入口失败测试**

创建 `tests/test_ale_cli.py` 的第一部分：

```python
from __future__ import annotations

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
ALE_CLI = ROOT / "scripts/ale.py"


def load_ale_cli():
    spec = importlib.util.spec_from_file_location("ale_cli", ALE_CLI)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AleCliTests(unittest.TestCase):
    def test_command_specs_use_repository_owned_entries(self) -> None:
        module = load_ale_cli()
        specs = module.command_specs(ROOT)
        self.assertIn("backend", specs)
        self.assertIn("frontend", specs)
        self.assertIn("control-plane", specs)
        backend_commands = [item.argv for item in specs["backend"]]
        self.assertTrue(any("scripts/selftest_smoke.py" in " ".join(item) for item in backend_commands))
        frontend_commands = [item.argv for item in specs["frontend"]]
        self.assertTrue(any("run build" in " ".join(item) for item in frontend_commands))

    def test_runner_stops_on_first_failure_and_returns_original_code(self) -> None:
        module = load_ale_cli()
        commands = [
            module.CommandSpec("first", ROOT, ["python", "-c", "raise SystemExit(7)"]),
            module.CommandSpec("second", ROOT, ["python", "-c", "raise SystemExit(0)"]),
        ]
        result = module.run_specs(commands)
        self.assertEqual(result, 7)

    def test_doctor_does_not_install_or_search_for_tools(self) -> None:
        text = ALE_CLI.read_text(encoding="utf-8")
        self.assertNotIn("pip install", text)
        self.assertNotIn("where.exe python", text)
        self.assertNotIn("Get-ChildItem C:", text)
```

- [ ] **Step 2: 运行测试并确认 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_cli.AleCliTests -v
```

Expected: `FAIL`，原因是 `scripts/ale.py` 不存在。

- [ ] **Step 3: 实现薄调度入口和开发依赖文件**

`backend/requirements-dev.txt` 精确内容：

```text
-r requirements.txt
httpx==0.28.1
```

`.gitignore` 增加：

```text
.ale-runs/
```

`scripts/ale.py` 使用以下接口：

```python
@dataclass(frozen=True)
class CommandSpec:
    name: str
    cwd: Path
    argv: list[str]


def project_python(root: Path) -> Path:
    return root / ".venv" / "Scripts" / "python.exe"


def npm_command() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def command_specs(root: Path) -> dict[str, list[CommandSpec]]:
    python = str(project_python(root))
    return {
        "control-plane": [
            CommandSpec(
                "control-plane-tests", root,
                [python, "-m", "unittest", "discover", "-s", "tests", "-p", "test_ale*.py", "-v"],
            ),
            CommandSpec(
                "project-state", root,
                [python, "scripts/check_project_state.py", "--format", "json"],
            ),
        ],
        "backend": [
            CommandSpec("backend-compile", root, [python, "-m", "compileall", "backend/app"]),
            CommandSpec("backend-selftest", root, [python, "scripts/selftest_smoke.py"]),
        ],
        "frontend": [
            CommandSpec("frontend-build", root / "frontend", [npm_command(), "run", "build"]),
        ],
    }


def run_specs(specs: list[CommandSpec]) -> int:
    for spec in specs:
        completed = subprocess.run(spec.argv, cwd=spec.cwd, check=False)
        if completed.returncode != 0:
            return completed.returncode
    return 0
```

`doctor` 必须逐项检查：Git 仓库、当前分支、`.venv/Scripts/python.exe`、
`import fastapi, httpx, cryptography`、`node --version`、`npm.cmd --version`、
`frontend/node_modules`、`config/local.yaml` 包含指向项目 `.selftest` 的 `local_root`、
以及 Task 2 状态检查。任何失败都输出单一可操作错误并返回 `1`，不得安装依赖或搜索整机。

`focused --target` 只接受 `control-plane/backend/frontend`；`exit` 固定按
`doctor -> control-plane -> backend -> frontend -> git diff --check` 顺序执行。

- [ ] **Step 4: 运行 CLI 测试和三个聚焦入口**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_cli.AleCliTests -v
.\.venv\Scripts\python.exe scripts\ale.py doctor
.\.venv\Scripts\python.exe scripts\ale.py focused --target control-plane
.\.venv\Scripts\python.exe scripts\ale.py focused --target backend
.\.venv\Scripts\python.exe scripts\ale.py focused --target frontend
```

Expected: 所有命令退出 `0`；后端自检显示 `24/24`；Vite 构建成功，可保留已知 chunk 体积警告。

- [ ] **Step 5: 提交 Task 3**

Run:

```powershell
git diff --check
git add -- .gitignore backend/requirements-dev.txt scripts/ale.py tests/test_ale_cli.py
git diff --cached --check
git commit -m "feat(ale): 增加确定性验证入口"
```

Expected: 提交只包含调度入口、开发依赖、忽略规则和测试。

---

### Task 4: 实现失败来源证明

**Files:**
- Modify: `scripts/ale.py`
- Modify: `tests/test_ale_cli.py`

**Interfaces:**
- Consumes: Task 3 的 `CommandSpec` 与项目根目录解析。
- Produces: `classify_failure(first_exit: int, baseline_exit: int | None, rerun_exit: int | None) -> str`、`sanitize_summary(text: str) -> str`、`run_provenance(task_id: str, command: list[str], current_root: Path, baseline_root: Path, baseline_commit: str, output_root: Path) -> tuple[int, Path]` 和 `ale.py provenance` 子命令。

- [ ] **Step 1: 先补充失败分类和脱敏测试**

向 `tests/test_ale_cli.py` 增加：

```python
    def test_failure_classification_preserves_first_failure(self) -> None:
        module = load_ale_cli()
        self.assertEqual(module.classify_failure(1, 0, 1), "branch_regression")
        self.assertEqual(module.classify_failure(1, 1, 1), "baseline_failure")
        self.assertEqual(module.classify_failure(1, None, 0), "gate_unstable")
        self.assertEqual(module.classify_failure(1, None, None), "unclassified")

    def test_summary_redacts_common_secret_shapes(self) -> None:
        module = load_ale_cli()
        raw = "Authorization: Bearer abcdefghijk api_key=sk-1234567890abcdef"
        cleaned = module.sanitize_summary(raw)
        self.assertNotIn("abcdefghijk", cleaned)
        self.assertNotIn("sk-1234567890abcdef", cleaned)
        self.assertIn("[REDACTED]", cleaned)

    def test_provenance_requires_distinct_frozen_baseline_checkout(self) -> None:
        module = load_ale_cli()
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw) / ".ale-runs"
            with self.assertRaises(ValueError):
                module.run_provenance(
                    task_id="ALE-TEST",
                    command=["python", "-c", "raise SystemExit(1)"],
                    current_root=ROOT,
                    baseline_root=ROOT,
                    baseline_commit="4ed88a90a07ff44383be17ade63eb4e677e053df",
                    output_root=output,
                )
```

- [ ] **Step 2: 运行新增测试并确认 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_cli.AleCliTests.test_failure_classification_preserves_first_failure tests.test_ale_cli.AleCliTests.test_summary_redacts_common_secret_shapes tests.test_ale_cli.AleCliTests.test_provenance_requires_distinct_frozen_baseline_checkout -v
```

Expected: `FAIL`，缺少 `classify_failure`、`sanitize_summary` 或 `run_provenance`。

- [ ] **Step 3: 最小实现 provenance 子命令**

在 `scripts/ale.py` 增加：

```python
def classify_failure(
    first_exit: int,
    baseline_exit: int | None,
    rerun_exit: int | None,
) -> str:
    if first_exit == 0:
        raise ValueError("provenance requires an observed first failure")
    if rerun_exit == 0:
        return "gate_unstable"
    if baseline_exit == 0:
        return "branch_regression"
    if baseline_exit is not None:
        return "baseline_failure"
    return "unclassified"


SECRET_PATTERNS = (
    re.compile(r"(?i)Authorization:\s*Bearer\s+\S+"),
    re.compile(r"(?i)(api[_-]?key|password|secret|token)\s*[:=]\s*\S+"),
    re.compile(r"sk-[A-Za-z0-9_-]{12,}"),
)


def sanitize_summary(text: str) -> str:
    cleaned = text
    for pattern in SECRET_PATTERNS:
        cleaned = pattern.sub("[REDACTED]", cleaned)
    return cleaned[:4000]
```

`run_provenance` 必须：

1. 拒绝相同的 `current_root` 与 `baseline_root`；
2. 校验 `baseline_root` 是 Git checkout，且 `HEAD == baseline_commit`；
3. 在当前 checkout 执行并捕获首次命令；
4. 首次失败后在冻结基线执行完全相同命令；
5. 在当前 checkout 最多诊断复跑一次；
6. 调用 `classify_failure`；
7. 将脱敏 JSON 写入 `.ale-runs/{task_id}-{utc_timestamp}.json`；
8. JSON 保留首次退出码，不允许复跑成功把结果字段改为通过；
9. 返回首次退出码和证据路径。

CLI 形状固定为：

```text
$env:ALE_BASELINE_WORKTREE = 'D:\tmp\teachingassist-ale-baseline'
python scripts/ale.py provenance --task-id ALE-TA-1 --baseline-root $env:ALE_BASELINE_WORKTREE --baseline-commit 4ed88a90a07ff44383be17ade63eb4e677e053df -- .\.venv\Scripts\python.exe -m unittest tests.test_ale_cli -v
```

- [ ] **Step 4: 运行 provenance 测试与回归**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_cli -v
.\.venv\Scripts\python.exe scripts\ale.py focused --target control-plane
```

Expected: 所有 CLI 测试和控制面测试通过；`.ale-runs/` 保持未跟踪不可见。

- [ ] **Step 5: 提交 Task 4**

Run:

```powershell
git diff --check
git add -- scripts/ale.py tests/test_ale_cli.py
git diff --cached --check
git commit -m "feat(ale): 增加失败来源证明"
```

Expected: 提交只包含 CLI 与对应测试。

---

### Task 5: 进入 ALE-TA-1 人工验收门

**Files:**
- Modify: `PROJECT_STATE.yaml`
- Modify: `CURRENT_ROUTE.md`
- Modify: `docs/ale_ta_1_manual_acceptance.md`
- Modify: `tests/test_ale_protocol.py`

**Interfaces:**
- Consumes: Task 1–4 的权威文件、检查器、验证入口和提交哈希。
- Produces: `awaiting_manual_acceptance` 状态、完整验收包和冷启动恢复说明。

- [ ] **Step 1: 写人工验收门状态失败测试**

向 `tests/test_ale_protocol.py` 增加：

```python
    def test_ale_ta_1_stops_at_human_acceptance_gate(self) -> None:
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        self.assertEqual(state["control_plane"]["status"], "awaiting_manual_acceptance")
        self.assertEqual(state["control_plane"]["manual_acceptance"], "pending")
        self.assertFalse(state["git"]["merge_main_allowed"])
        self.assertFalse(state["git"]["push_origin_main_allowed"])
        self.assertFalse(state["verification"]["automated_tests_equal_human_acceptance"])

        package = (ROOT / "docs/ale_ta_1_manual_acceptance.md").read_text(encoding="utf-8")
        for term in (
            "outcome_batch: ALE-TA-1",
            "status: awaiting_manual_acceptance",
            "24/24",
            "npm.cmd run build",
            "Human decision",
            "accepted / repair_required / rejected",
        ):
            self.assertIn(term, package)
```

- [ ] **Step 2: 运行该测试并确认 RED**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ale_protocol.AleProtocolContractTests.test_ale_ta_1_stops_at_human_acceptance_gate -v
```

Expected: `FAIL`，当前状态仍为 `in_progress`。

- [ ] **Step 3: 运行完整退出门并记录新鲜证据**

Run:

```powershell
.\.venv\Scripts\python.exe scripts\ale.py exit
```

Expected:

- doctor 通过；
- 控制面测试全部通过；
- `scripts/check_project_state.py --format json` 返回 `passed: true`；
- 后端 compileall 通过；
- `scripts/selftest_smoke.py` 显示 `24/24`；
- 前端 `tsc && vite build` 通过；
- `git diff --check` 通过；
- 退出码 `0`。

- [ ] **Step 4: 更新状态、路线和验收包**

将 `PROJECT_STATE.yaml` 更新为：

```json
"control_plane": {
  "outcome_batch": "ALE-TA-1",
  "name": "ALE v1.5.0 TeachingAssist Adaptation",
  "status": "awaiting_manual_acceptance",
  "manual_acceptance": "pending",
  "bootstrap_in_place_allowed": true,
  "follow_up_gate": "human_acceptance_required"
},
"verification": {
  "technical_verification": "passed",
  "focused_control_plane": "passed",
  "backend_verification": "passed_24_of_24",
  "frontend_verification": "passed_with_existing_chunk_size_warning",
  "automated_tests_equal_human_acceptance": false
}
```

验收包必须记录：Outcome 和硬边界、Task 1–4 提交、变更文件、实际命令和结果、
已知的 Vite chunk 警告、冷启动读取顺序、`doctor/focused/exit/provenance` 人工检查、
以及 `accepted / repair_required / rejected` 决策字段。`CURRENT_ROUTE.md` 同步为
`ALE-TA-1 awaiting manual acceptance`，但仍明确产品路线停在真实机房试点。

- [ ] **Step 5: 运行最终 GREEN 和一致性复核**

Run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_ale*.py" -v
.\.venv\Scripts\python.exe scripts\check_project_state.py --format json
.\.venv\Scripts\python.exe scripts\ale.py doctor
git diff --check
git status --short --branch
```

Expected: 所有测试通过，状态检查 `passed: true`，当前分支为
`codex/ale-v1-5-adaptation`，仅本任务四个状态/验收文件有未提交修改。

- [ ] **Step 6: 精确提交人工验收门并停止**

Run:

```powershell
git add -- PROJECT_STATE.yaml CURRENT_ROUTE.md docs/ale_ta_1_manual_acceptance.md tests/test_ale_protocol.py
git diff --cached --check
git commit -m "chore(ale): 进入 ALE-TA-1 人工验收门"
git status --short --branch
git log --oneline -n 7
```

Expected: 工作树干净；分支未 push；`main` 与 `origin/main` 仍为
`4ed88a90a07ff44383be17ade63eb4e677e053df`。输出 Human Acceptance Handoff 并停止，
不得自动 accepted、merge 或进入新的产品 Outcome。

## Final Self-Review Checklist

- [ ] 设计第 1–11 节均有对应 Task。
- [ ] 所有新增接口在首次使用前已给出精确签名。
- [ ] 所有测试步骤都有明确 RED 或 GREEN 预期。
- [ ] 所有提交命令列出精确文件，没有 `git add .`。
- [ ] 源项目保持只读，计划中没有源路径写入命令。
- [ ] 产品运行代码、API、Schema、React 页面和 Provider 不在变更清单中。
- [ ] Full ALE 最终停在人工验收门，未授权 push/merge 保持禁止。
