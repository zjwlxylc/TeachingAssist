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


def initialize_repository(repo: Path) -> str:
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "ale@example.invalid"],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "ALE Test"],
        cwd=repo,
        check=True,
    )
    (repo / "allowed.txt").write_text("base\n", encoding="utf-8")
    (repo / "outside.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", "allowed.txt", "outside.txt"],
        cwd=repo,
        check=True,
    )
    subprocess.run(["git", "commit", "-m", "baseline"], cwd=repo, check=True)
    baseline = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/remotes/origin/main", baseline],
        cwd=repo,
        check=True,
    )
    subprocess.run(
        ["git", "switch", "-c", "codex/fast-test"],
        cwd=repo,
        check=True,
    )
    return baseline


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

    def test_bootstrap_exception_is_limited_to_ale_ta_1_open_states(self) -> None:
        module = load_checker()
        state = json.loads((ROOT / "PROJECT_STATE.yaml").read_text(encoding="utf-8"))
        state["control_plane"]["status"] = "accepted_closed"
        failures = module.check_state_schema(state)
        self.assertTrue(any("bootstrap_in_place_allowed" in item for item in failures))

    def test_fast_report_rejects_out_of_scope_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            baseline = initialize_repository(repo)
            (repo / "outside.txt").write_text("changed\n", encoding="utf-8")
            report = load_checker().build_fast_report(
                repo, baseline, "codex/fast-test", ["allowed.txt"]
            )
            self.assertFalse(report["passed"])
            self.assertTrue(any("outside.txt" in item for item in report["failures"]))

    def test_fast_report_accepts_only_the_exact_allowed_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            baseline = initialize_repository(repo)
            (repo / "allowed.txt").write_text("changed\n", encoding="utf-8")
            report = load_checker().build_fast_report(
                repo, baseline, "codex/fast-test", ["allowed.txt"]
            )
            self.assertTrue(report["passed"], report["failures"])

    def test_fast_report_rejects_parent_and_absolute_allowed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            repo = Path(raw)
            baseline = initialize_repository(repo)
            module = load_checker()
            parent_report = module.build_fast_report(
                repo, baseline, "codex/fast-test", ["../outside.txt"]
            )
            absolute_report = module.build_fast_report(
                repo, baseline, "codex/fast-test", [str(repo / "allowed.txt")]
            )
            self.assertFalse(parent_report["passed"])
            self.assertFalse(absolute_report["passed"])


if __name__ == "__main__":
    unittest.main()
