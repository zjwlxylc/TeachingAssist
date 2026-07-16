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

    def test_development_requirements_include_smoke_test_dependency(self) -> None:
        requirements = (ROOT / "backend/requirements-dev.txt").read_text(encoding="utf-8")
        self.assertEqual(requirements.splitlines(), ["-r requirements.txt", "httpx==0.28.1"])

    def test_ale_run_evidence_is_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
        self.assertIn(".ale-runs/", ignored)


if __name__ == "__main__":
    unittest.main()
