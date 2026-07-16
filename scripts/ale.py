import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_TARGETS = ("control-plane", "backend", "frontend")


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
    root = root.resolve()
    python = str(project_python(root))
    return {
        "control-plane": [
            CommandSpec(
                "control-plane-tests",
                root,
                [
                    python,
                    "-m",
                    "unittest",
                    "discover",
                    "-s",
                    "tests",
                    "-p",
                    "test_ale*.py",
                    "-v",
                ],
            ),
            CommandSpec(
                "project-state",
                root,
                [python, "scripts/check_project_state.py", "--format", "json"],
            ),
        ],
        "backend": [
            CommandSpec(
                "backend-compile",
                root,
                [python, "-m", "compileall", "backend/app"],
            ),
            CommandSpec(
                "backend-selftest",
                root,
                [python, "scripts/selftest_smoke.py"],
            ),
        ],
        "frontend": [
            CommandSpec(
                "frontend-build",
                root / "frontend",
                [npm_command(), "run", "build"],
            ),
        ],
    }


def run_specs(specs: list[CommandSpec]) -> int:
    for spec in specs:
        print(f"==> {spec.name}")
        try:
            completed = subprocess.run(spec.argv, cwd=spec.cwd, check=False)
        except OSError as exc:
            print(f"ALE command could not start: {spec.name}: {exc}", file=sys.stderr)
            return 1
        if completed.returncode != 0:
            print(
                f"ALE command failed: {spec.name} (exit {completed.returncode})",
                file=sys.stderr,
            )
            return completed.returncode
    return 0


def _capture(argv: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _doctor_error(message: str) -> int:
    print(f"ALE doctor: FAIL - {message}", file=sys.stderr)
    return 1


def _configured_local_root(config_path: Path) -> Path | None:
    if not config_path.is_file():
        return None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*local_root:\s*(.+?)\s*$", line)
        if match:
            raw = match.group(1).strip().strip("'\"")
            return Path(raw) if raw else None
    return None


def doctor(root: Path) -> int:
    root = root.resolve()
    git_root = _capture(
        ["git", "-c", "core.quotepath=false", "rev-parse", "--show-toplevel"],
        root,
    )
    if git_root.returncode != 0:
        return _doctor_error("run the command from the TeachingAssist Git checkout")
    if Path(git_root.stdout.strip()).resolve() != root:
        return _doctor_error(f"project root must be {root}")

    state_path = root / "PROJECT_STATE.yaml"
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        expected_branch = state["git"]["authorized_work_branch"]
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        return _doctor_error(f"repair PROJECT_STATE.yaml before continuing: {exc}")
    current_branch = _capture(
        ["git", "-c", "core.quotepath=false", "branch", "--show-current"],
        root,
    )
    if current_branch.returncode != 0 or current_branch.stdout.strip() != expected_branch:
        return _doctor_error(f"switch to authorized branch {expected_branch}")

    python = project_python(root)
    if not python.is_file():
        return _doctor_error("restore the repository .venv Python environment")
    imports = _capture(
        [str(python), "-c", "import fastapi, httpx, cryptography"],
        root,
    )
    if imports.returncode != 0:
        return _doctor_error(
            "install backend/requirements-dev.txt into the existing .venv"
        )

    node = _capture(["node", "--version"], root)
    if node.returncode != 0:
        return _doctor_error("make the project-compatible Node runtime available")
    npm = _capture([npm_command(), "--version"], root)
    if npm.returncode != 0:
        return _doctor_error("make npm available beside the Node runtime")
    if not (root / "frontend" / "node_modules").is_dir():
        return _doctor_error("restore frontend/node_modules from the existing lockfile")

    configured_root = _configured_local_root(root / "config" / "local.yaml")
    expected_local_root = (root / ".selftest").resolve()
    if configured_root is None or configured_root.resolve() != expected_local_root:
        return _doctor_error(
            f"set config/local.yaml storage.local_root to {expected_local_root}"
        )

    state_check = _capture(
        [str(python), "scripts/check_project_state.py", "--format", "json"],
        root,
    )
    if state_check.returncode != 0:
        summary = state_check.stdout.strip() or state_check.stderr.strip()
        return _doctor_error(f"repair ALE project state: {summary[:800]}")

    print(
        "ALE doctor: PASS "
        f"(branch={expected_branch}, python={python.name}, "
        f"node={node.stdout.strip()}, npm={npm.stdout.strip()})"
    )
    return 0


def focused(root: Path, target: str) -> int:
    specs = command_specs(root)
    if target not in specs:
        print(
            f"ALE focused: unknown target {target!r}; choose {', '.join(VALID_TARGETS)}",
            file=sys.stderr,
        )
        return 1
    return run_specs(specs[target])


def exit_gate(root: Path) -> int:
    result = doctor(root)
    if result != 0:
        return result
    for target in VALID_TARGETS:
        result = focused(root, target)
        if result != 0:
            return result
    return run_specs(
        [
            CommandSpec(
                "git-diff-check",
                root.resolve(),
                ["git", "-c", "core.quotepath=false", "diff", "--check"],
            )
        ]
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="TeachingAssist ALE v1.5.0 runner")
    parser.add_argument("--project-root", type=Path, default=ROOT)
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("doctor", help="check the known project environment")
    focused_parser = subcommands.add_parser("focused", help="run a focused gate")
    focused_parser.add_argument("--target", choices=VALID_TARGETS, required=True)
    subcommands.add_parser("exit", help="run all exit gates in fixed order")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        return doctor(args.project_root)
    if args.command == "focused":
        return focused(args.project_root, args.target)
    if args.command == "exit":
        return exit_gate(args.project_root)
    return 1


if __name__ == "__main__":
    sys.exit(main())
