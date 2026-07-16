import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALID_TARGETS = ("control-plane", "backend", "frontend")
AUTHORIZATION_PATTERN = re.compile(
    r"(?i)([\"']?Authorization[\"']?\s*:\s*[\"']?Bearer\s+)([^\"'\s,}]+)"
)
SENSITIVE_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)([\"']?(?:api[_-]?key|password|secret|token)[\"']?\s*[:=]\s*)"
    r'(?:"[^"]*"|\'[^\']*\'|[^\s,}]+)'
)
SECRET_TOKEN_PATTERN = re.compile(r"sk-[A-Za-z0-9_-]{12,}")
SENSITIVE_COMMAND_FLAGS = {
    "--api-key",
    "--api_key",
    "--password",
    "--secret",
    "--token",
}


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
    try:
        return subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError as exc:
        return subprocess.CompletedProcess(argv, 127, "", str(exc))


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


def sanitize_summary(text: str) -> str:
    cleaned = AUTHORIZATION_PATTERN.sub(r"\1[REDACTED]", text)
    cleaned = SENSITIVE_ASSIGNMENT_PATTERN.sub(r"\1[REDACTED]", cleaned)
    cleaned = SECRET_TOKEN_PATTERN.sub("[REDACTED]", cleaned)
    return cleaned[:4000]


def sanitize_command(command: list[str]) -> list[str]:
    cleaned: list[str] = []
    redact_next = False
    for argument in command:
        if redact_next:
            cleaned.append("[REDACTED]")
            redact_next = False
            continue
        cleaned.append(sanitize_summary(argument))
        if argument.lower() in SENSITIVE_COMMAND_FLAGS:
            redact_next = True
    return cleaned


def _provenance_run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    try:
        return _capture(command, cwd)
    except OSError as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def _git_value(root: Path, *args: str) -> str:
    completed = _capture(
        ["git", "-c", "core.quotepath=false", *args],
        root,
    )
    if completed.returncode != 0:
        raise ValueError(completed.stderr.strip() or "Git identity check failed")
    return completed.stdout.strip()


def _run_evidence(completed: subprocess.CompletedProcess[str]) -> dict[str, object]:
    combined = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    )
    return {
        "exit_code": completed.returncode,
        "output_summary": sanitize_summary(combined),
    }


def run_provenance(
    task_id: str,
    command: list[str],
    current_root: Path,
    baseline_root: Path,
    baseline_commit: str,
    output_root: Path,
) -> tuple[int, Path]:
    current = current_root.resolve()
    baseline = baseline_root.resolve()
    if current == baseline:
        raise ValueError("baseline_root must be a distinct frozen checkout")
    if not command:
        raise ValueError("provenance requires a command")
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", task_id) is None:
        raise ValueError("task_id must contain only letters, digits, dot, underscore, or dash")

    current_git_root = Path(_git_value(current, "rev-parse", "--show-toplevel")).resolve()
    if current_git_root != current:
        raise ValueError("current_root must be a Git checkout root")
    baseline_git_root = Path(
        _git_value(baseline, "rev-parse", "--show-toplevel")
    ).resolve()
    if baseline_git_root != baseline:
        raise ValueError("baseline_root must be a Git checkout root")
    actual_baseline = _git_value(baseline, "rev-parse", "HEAD")
    if actual_baseline != baseline_commit:
        raise ValueError(
            f"baseline checkout HEAD is {actual_baseline}, expected {baseline_commit}"
        )
    baseline_status_before = _git_value(
        baseline, "status", "--porcelain=v1", "--untracked-files=all"
    )
    if baseline_status_before:
        raise ValueError("frozen baseline checkout must be clean before reproduction")

    current_branch = _git_value(current, "branch", "--show-current")
    current_head = _git_value(current, "rev-parse", "HEAD")
    first = _provenance_run(command, current)
    if first.returncode == 0:
        raise ValueError("provenance command passed; no first failure was observed")
    baseline_result = _provenance_run(command, baseline)
    baseline_head_after = _git_value(baseline, "rev-parse", "HEAD")
    baseline_status_after = _git_value(
        baseline, "status", "--porcelain=v1", "--untracked-files=all"
    )
    baseline_head_unchanged = baseline_head_after == baseline_commit
    baseline_clean_after = not baseline_status_after
    trusted_baseline_exit = (
        baseline_result.returncode
        if baseline_head_unchanged and baseline_clean_after
        else None
    )
    rerun = _provenance_run(command, current)
    classification = classify_failure(
        first.returncode,
        trusted_baseline_exit,
        rerun.returncode,
    )

    timestamp = datetime.now(timezone.utc)
    evidence = {
        "schema_version": 1,
        "task_id": task_id,
        "timestamp_utc": timestamp.isoformat().replace("+00:00", "Z"),
        "command": sanitize_command(command),
        "current": {
            "cwd": str(current),
            "branch": current_branch,
            "head": current_head,
        },
        "baseline": {
            "cwd": str(baseline),
            "commit": baseline_commit,
            "clean_before": True,
            "clean_after": baseline_clean_after,
            "head_unchanged": baseline_head_unchanged,
        },
        "first_run": _run_evidence(first),
        "baseline_run": _run_evidence(baseline_result),
        "diagnostic_rerun": _run_evidence(rerun),
        "classification": classification,
        "first_failure_preserved": True,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    filename_timestamp = timestamp.strftime("%Y%m%dT%H%M%S.%fZ")
    evidence_path = output_root / f"{task_id}-{filename_timestamp}.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    return first.returncode, evidence_path


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
    provenance_parser = subcommands.add_parser(
        "provenance", help="preserve and classify an observed command failure"
    )
    provenance_parser.add_argument("--task-id", required=True)
    provenance_parser.add_argument("--baseline-root", type=Path, required=True)
    provenance_parser.add_argument("--baseline-commit", required=True)
    provenance_parser.add_argument("command_argv", nargs=argparse.REMAINDER)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "doctor":
        return doctor(args.project_root)
    if args.command == "focused":
        return focused(args.project_root, args.target)
    if args.command == "exit":
        return exit_gate(args.project_root)
    if args.command == "provenance":
        command = list(args.command_argv)
        if command and command[0] == "--":
            command = command[1:]
        try:
            first_exit, evidence_path = run_provenance(
                task_id=args.task_id,
                command=command,
                current_root=args.project_root,
                baseline_root=args.baseline_root,
                baseline_commit=args.baseline_commit,
                output_root=args.project_root / ".ale-runs",
            )
        except (OSError, ValueError) as exc:
            print(f"ALE provenance: FAIL - {exc}", file=sys.stderr)
            return 1
        print(f"ALE provenance evidence: {evidence_path}")
        return first_exit
    return 1


if __name__ == "__main__":
    sys.exit(main())
