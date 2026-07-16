from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
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
        self.assertTrue(
            any("scripts/selftest_smoke.py" in " ".join(item) for item in backend_commands)
        )
        frontend_commands = [item.argv for item in specs["frontend"]]
        self.assertTrue(any("run build" in " ".join(item) for item in frontend_commands))

    def test_runner_stops_on_first_failure_and_returns_original_code(self) -> None:
        module = load_ale_cli()
        commands = [
            module.CommandSpec("first", ROOT, ["python", "-c", "raise SystemExit(7)"]),
            module.CommandSpec("second", ROOT, ["python", "-c", "raise SystemExit(0)"]),
        ]
        with patch.object(module.subprocess, "run", wraps=subprocess.run) as runner:
            result = module.run_specs(commands)
        self.assertEqual(result, 7)
        self.assertEqual(runner.call_count, 1)

    def test_doctor_does_not_install_or_search_for_tools(self) -> None:
        text = ALE_CLI.read_text(encoding="utf-8")
        self.assertNotIn("pip install", text)
        self.assertNotIn("where.exe python", text)
        self.assertNotIn("Get-ChildItem C:", text)

    def test_focused_rejects_unknown_target_without_running_commands(self) -> None:
        module = load_ale_cli()
        with patch.object(module, "run_specs") as runner:
            result = module.focused(ROOT, "unknown")
        self.assertEqual(result, 1)
        runner.assert_not_called()

    def test_capture_converts_missing_executable_to_nonzero_result(self) -> None:
        module = load_ale_cli()
        completed = module._capture(["ale-command-that-does-not-exist"], ROOT)
        self.assertEqual(completed.returncode, 127)
        self.assertTrue(completed.stderr)

    def test_development_requirements_include_smoke_test_dependency(self) -> None:
        requirements = (ROOT / "backend/requirements-dev.txt").read_text(encoding="utf-8")
        self.assertEqual(requirements.splitlines(), ["-r requirements.txt", "httpx==0.28.1"])

    def test_ale_run_evidence_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".ale-runs/", ignored)

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

    def test_summary_redacts_json_yaml_and_quoted_authorization(self) -> None:
        module = load_ale_cli()
        raw = (
            '{"password": "json-secret", "Authorization": "Bearer json-token"}\n'
            "api_key: yaml-secret\ntoken='quoted-secret'"
        )
        cleaned = module.sanitize_summary(raw)
        for secret in ("json-secret", "json-token", "yaml-secret", "quoted-secret"):
            self.assertNotIn(secret, cleaned)

    def test_command_redacts_values_following_sensitive_flags(self) -> None:
        module = load_ale_cli()
        cleaned = module.sanitize_command(
            ["tool", "--token", "flag-secret", "--api-key=inline-secret", "safe"]
        )
        self.assertEqual(
            cleaned,
            ["tool", "--token", "[REDACTED]", "--api-key=[REDACTED]", "safe"],
        )

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

    def test_provenance_evidence_keeps_the_first_exit_code(self) -> None:
        module = load_ale_cli()
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            baseline_root = temporary / "baseline"
            baseline_root.mkdir()
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "ale@example.invalid"],
                cwd=baseline_root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "ALE Test"],
                cwd=baseline_root,
                check=True,
            )
            (baseline_root / "baseline.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "baseline.txt"], cwd=baseline_root, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "baseline"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
            )
            baseline_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip()
            first_exit, evidence_path = module.run_provenance(
                task_id="ALE-TEST",
                command=[sys.executable, "-c", "raise SystemExit(5)"],
                current_root=ROOT,
                baseline_root=baseline_root,
                baseline_commit=baseline_commit,
                output_root=temporary / ".ale-runs",
            )
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            self.assertEqual(first_exit, 5)
            self.assertEqual(evidence["first_run"]["exit_code"], 5)
            self.assertEqual(evidence["classification"], "baseline_failure")
            self.assertTrue(evidence["baseline"]["clean_before"])
            self.assertTrue(evidence["baseline"]["clean_after"])
            self.assertTrue(evidence["baseline"]["head_unchanged"])

    def test_provenance_rejects_a_dirty_baseline_checkout(self) -> None:
        module = load_ale_cli()
        with tempfile.TemporaryDirectory() as raw:
            temporary = Path(raw)
            baseline_root = temporary / "baseline"
            baseline_root.mkdir()
            subprocess.run(
                ["git", "init", "-b", "main"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "ale@example.invalid"],
                cwd=baseline_root,
                check=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "ALE Test"],
                cwd=baseline_root,
                check=True,
            )
            (baseline_root / "baseline.txt").write_text("base\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "baseline.txt"], cwd=baseline_root, check=True
            )
            subprocess.run(
                ["git", "commit", "-m", "baseline"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
            )
            baseline_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=baseline_root,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
            ).stdout.strip()
            (baseline_root / "unexpected.txt").write_text("dirty\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "frozen baseline checkout must be clean"):
                module.run_provenance(
                    task_id="ALE-DIRTY",
                    command=[sys.executable, "-c", "raise SystemExit(5)"],
                    current_root=ROOT,
                    baseline_root=baseline_root,
                    baseline_commit=baseline_commit,
                    output_root=temporary / ".ale-runs",
                )


if __name__ == "__main__":
    unittest.main()
