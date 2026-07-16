from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Any


STATE_FILE = "PROJECT_STATE.yaml"
FULL_ALE_MODE = "full_ale"
FAST_LOOP_MODE = "deterministic_fast_loop"
FORBIDDEN_MACHINE_LOCAL_KEYS = {
    "worktree_root",
    "worktree_path",
    "git_common_dir",
    "runtime_head",
    "python_path",
    "node_path",
    "operator_identity",
    "runtime_identity",
}

REQUIRED_TOP_LEVEL_KEYS = {
    "schema_version",
    "as_of",
    "project",
    "ale_protocol_version",
    "authority",
    "git",
    "product_route",
    "control_plane",
    "boundaries",
    "verification",
}
REQUIRED_AUTHORITY_KEYS = {
    "current_route",
    "latest_handoff",
    "route_history",
    "manual_acceptance_package",
}
REQUIRED_GIT_KEYS = {
    "baseline_branch",
    "baseline_commit",
    "authorized_work_branch",
    "push_work_branch_allowed",
    "merge_main_allowed",
    "push_origin_main_allowed",
}
MANUAL_ACCEPTANCE_BY_STATUS = {
    "in_progress": "not_performed",
    "awaiting_manual_acceptance": "pending",
    "accepted_closed": "accepted",
    "acceptance_repair_required": "repair_required",
    "rejected_closed": "rejected",
}
OPEN_BOOTSTRAP_STATES = {"in_progress", "awaiting_manual_acceptance"}
EXPECTED_RUNTIME_IGNORED_PREFIXES = (
    ".ale-runs/",
    ".claude/",
    ".idea/",
    ".runtime/",
    ".selftest/",
    ".venv/",
    ".vscode/",
    ".workbuddy/",
    "build/",
    "dist/",
    "frontend/.vite/",
    "frontend/dist/",
    "frontend/node_modules/",
)
EXPECTED_RUNTIME_IGNORED_SUFFIXES = (
    ".7z",
    ".db",
    ".exe",
    ".log",
    ".pyc",
    ".pyo",
    ".spec",
    ".sqlite",
    ".sqlite3",
    ".zip",
)


def _git(
    root: Path,
    *args: str,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", "core.quotepath=false", *args],
        cwd=root,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _git_text(root: Path, *args: str) -> str:
    return _git(root, *args, check=True).stdout.strip()


def _mapping(value: object, name: str, failures: list[str]) -> dict[str, Any]:
    if not isinstance(value, dict):
        failures.append(f"{name} must be an object")
        return {}
    return value


def _walk_keys(value: object, prefix: str = "") -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for raw_key, child in value.items():
            key = str(raw_key)
            path = f"{prefix}.{key}" if prefix else key
            found.append((key, path))
            found.extend(_walk_keys(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_walk_keys(child, f"{prefix}[{index}]"))
    return found


def load_state(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("PROJECT_STATE.yaml must contain a JSON object")
    return value


def check_state_schema(state: dict[str, object]) -> list[str]:
    failures: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(state))
    if missing:
        failures.append(f"missing top-level state keys: {', '.join(missing)}")

    if state.get("schema_version") != 1:
        failures.append("schema_version must be 1")
    if state.get("project") != "TeachingAssist":
        failures.append("project must be TeachingAssist")
    if state.get("ale_protocol_version") != "1.5.0":
        failures.append("ale_protocol_version must be 1.5.0")

    for key, path in _walk_keys(state):
        if key in FORBIDDEN_MACHINE_LOCAL_KEYS:
            failures.append(f"machine-local state key is forbidden: {path}")

    authority = _mapping(state.get("authority"), "authority", failures)
    missing_authority = sorted(REQUIRED_AUTHORITY_KEYS - set(authority))
    if missing_authority:
        failures.append(f"missing authority keys: {', '.join(missing_authority)}")

    git_state = _mapping(state.get("git"), "git", failures)
    missing_git = sorted(REQUIRED_GIT_KEYS - set(git_state))
    if missing_git:
        failures.append(f"missing git keys: {', '.join(missing_git)}")
    for permission in (
        "push_work_branch_allowed",
        "merge_main_allowed",
        "push_origin_main_allowed",
    ):
        if permission in git_state and not isinstance(git_state[permission], bool):
            failures.append(f"git.{permission} must be boolean")
    control = _mapping(state.get("control_plane"), "control_plane", failures)
    status = control.get("status")
    manual_acceptance = control.get("manual_acceptance")
    expected_manual = MANUAL_ACCEPTANCE_BY_STATUS.get(status)
    if expected_manual is None:
        failures.append(f"unsupported control_plane.status: {status}")
    elif manual_acceptance != expected_manual:
        failures.append(
            "control_plane.manual_acceptance does not match status: "
            f"expected {expected_manual}, got {manual_acceptance}"
        )

    accepted_closeout = status == "accepted_closed" and manual_acceptance == "accepted"
    if git_state.get("merge_main_allowed") is not False and not accepted_closeout:
        failures.append("git.merge_main_allowed must remain false before acceptance")
    if git_state.get("push_origin_main_allowed") is not False and not accepted_closeout:
        failures.append("git.push_origin_main_allowed must remain false before acceptance")

    bootstrap_allowed = control.get("bootstrap_in_place_allowed")
    if not isinstance(bootstrap_allowed, bool):
        failures.append("control_plane.bootstrap_in_place_allowed must be boolean")
    elif bootstrap_allowed and (
        control.get("outcome_batch") != "ALE-TA-1" or status not in OPEN_BOOTSTRAP_STATES
    ):
        failures.append(
            "bootstrap_in_place_allowed is limited to ALE-TA-1 open states"
        )

    boundaries = _mapping(state.get("boundaries"), "boundaries", failures)
    for key, value in boundaries.items():
        if not isinstance(value, bool):
            failures.append(f"boundaries.{key} must be boolean")
        elif value:
            failures.append(f"boundaries.{key} must remain false for ALE-TA-1")

    verification = _mapping(state.get("verification"), "verification", failures)
    if verification.get("automated_tests_equal_human_acceptance") is not False:
        failures.append(
            "verification.automated_tests_equal_human_acceptance must be false"
        )
    return failures


def _safe_relative_path(value: object) -> tuple[Path | None, str | None]:
    if not isinstance(value, str) or not value.strip():
        return None, "must be a non-empty repository-relative path"
    if "\\" in value:
        return None, "must use forward slashes"
    pure = PurePosixPath(value)
    if pure.is_absolute() or ".." in pure.parts or pure.parts[0] in {"", "."}:
        return None, "must stay within the repository"
    if ":" in pure.parts[0]:
        return None, "must not be an absolute Windows path"
    return Path(*pure.parts), None


def check_authority_paths(
    state: dict[str, object], project_root: Path
) -> list[str]:
    failures: list[str] = []
    authority = _mapping(state.get("authority"), "authority", failures)
    root = project_root.resolve()
    for key in sorted(REQUIRED_AUTHORITY_KEYS):
        relative, error = _safe_relative_path(authority.get(key))
        if error is not None:
            failures.append(f"authority.{key} {error}")
            continue
        assert relative is not None
        target = (root / relative).resolve()
        try:
            target.relative_to(root)
        except ValueError:
            failures.append(f"authority.{key} escapes the repository")
            continue
        if not target.is_file():
            failures.append(f"authority.{key} does not exist: {relative.as_posix()}")
    return failures


def check_document_consistency(
    state: dict[str, object], project_root: Path
) -> list[str]:
    failures: list[str] = []
    authority = _mapping(state.get("authority"), "authority", failures)
    control = _mapping(state.get("control_plane"), "control_plane", failures)
    route_value = authority.get("current_route")
    handoff_value = authority.get("manual_acceptance_package")
    route_relative, route_error = _safe_relative_path(route_value)
    handoff_relative, handoff_error = _safe_relative_path(handoff_value)
    if route_error is not None or route_relative is None:
        failures.append("cannot check route consistency without a valid current_route")
        return failures
    if handoff_error is not None or handoff_relative is None:
        failures.append("cannot check handoff consistency without a valid acceptance package")
        return failures

    route_path = project_root / route_relative
    handoff_path = project_root / handoff_relative
    if not route_path.is_file() or not handoff_path.is_file():
        return failures

    route = route_path.read_text(encoding="utf-8")
    handoff = handoff_path.read_text(encoding="utf-8")
    if len(route.splitlines()) > 140:
        failures.append("CURRENT_ROUTE.md exceeds 140 lines")
    if STATE_FILE not in route or "single machine authority" not in route:
        failures.append("CURRENT_ROUTE.md must point to the single machine authority")

    outcome = str(control.get("outcome_batch", ""))
    status = str(control.get("status", ""))
    if outcome and outcome not in route:
        failures.append(f"CURRENT_ROUTE.md does not mention outcome {outcome}")
    if status and status not in route:
        failures.append(f"CURRENT_ROUTE.md does not mention status {status}")
    if f"outcome_batch: {outcome}" not in handoff:
        failures.append("manual acceptance package outcome does not match state")
    if f"status: {status}" not in handoff:
        failures.append("manual acceptance package status does not match state")
    if "Automated verification does not equal human acceptance." not in handoff:
        failures.append("manual acceptance package is missing the acceptance boundary")
    return failures


def check_git_consistency(
    state: dict[str, object], git_root: Path
) -> list[str]:
    failures: list[str] = []
    git_state = _mapping(state.get("git"), "git", failures)
    control = _mapping(state.get("control_plane"), "control_plane", failures)
    baseline = str(git_state.get("baseline_commit", ""))
    branch = str(git_state.get("authorized_work_branch", ""))
    baseline_branch = str(git_state.get("baseline_branch", ""))

    try:
        actual_root = Path(_git_text(git_root, "rev-parse", "--show-toplevel")).resolve()
    except subprocess.CalledProcessError:
        return ["project root is not a Git repository"]
    if actual_root != git_root.resolve():
        failures.append(f"Git root mismatch: expected {git_root.resolve()}, got {actual_root}")

    verify = _git(git_root, "rev-parse", "--verify", f"{baseline}^{{commit}}")
    if not baseline or verify.returncode != 0:
        failures.append(f"baseline commit is unavailable: {baseline}")
        return failures
    resolved_baseline = verify.stdout.strip()
    if resolved_baseline != baseline:
        failures.append("baseline_commit must be a full resolved commit SHA")

    current_branch = _git_text(git_root, "branch", "--show-current")
    if current_branch != branch:
        failures.append(f"current branch must be {branch}, got {current_branch}")
    ancestor = _git(git_root, "merge-base", "--is-ancestor", baseline, "HEAD")
    if ancestor.returncode != 0:
        failures.append("baseline commit is not an ancestor of HEAD")

    head = _git_text(git_root, "rev-parse", "HEAD")
    accepted_main_integration = (
        control.get("status") == "accepted_closed"
        and control.get("manual_acceptance") == "accepted"
        and branch == baseline_branch
        and git_state.get("merge_main_allowed") is True
        and git_state.get("push_origin_main_allowed") is True
    )
    protected_refs = (
        f"refs/heads/{baseline_branch}",
        f"refs/remotes/origin/{baseline_branch}",
    )
    for reference in protected_refs:
        resolved = _git(git_root, "rev-parse", "--verify", reference)
        if resolved.returncode != 0:
            failures.append(f"protected ref is missing: {reference}")
            continue
        actual = resolved.stdout.strip()
        if accepted_main_integration:
            allowed = {head} if reference.startswith("refs/heads/") else {baseline, head}
        else:
            allowed = {baseline}
        if actual not in allowed:
            failures.append(
                f"protected ref moved: {reference}={actual}, expected one of {sorted(allowed)}"
            )
    return failures


def _worktree_entries(git_root: Path) -> list[dict[str, str]]:
    output = _git_text(git_root, "worktree", "list", "--porcelain")
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    for line in output.splitlines() + [""]:
        if not line:
            if current:
                entries.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        current[key] = value
    return entries


def check_worktree_consistency(
    state: dict[str, object], git_root: Path
) -> list[str]:
    failures: list[str] = []
    git_state = _mapping(state.get("git"), "git", failures)
    control = _mapping(state.get("control_plane"), "control_plane", failures)
    branch = str(git_state.get("authorized_work_branch", ""))
    baseline_branch = str(git_state.get("baseline_branch", ""))
    root = git_root.resolve()

    try:
        entries = _worktree_entries(root)
    except subprocess.CalledProcessError:
        return ["unable to read Git worktree identity"]
    matches = [
        entry
        for entry in entries
        if entry.get("worktree") and Path(entry["worktree"]).resolve() == root
    ]
    if len(matches) != 1:
        failures.append("current checkout has no unique Git worktree identity")
        return failures
    if matches[0].get("branch") != f"refs/heads/{branch}":
        failures.append("current worktree does not own the authorized work branch")

    git_marker = root / ".git"
    is_linked_worktree = git_marker.is_file()
    bootstrap_allowed = control.get("bootstrap_in_place_allowed") is True
    accepted_main_checkout = (
        control.get("status") == "accepted_closed"
        and control.get("manual_acceptance") == "accepted"
        and branch == baseline_branch
        and git_state.get("merge_main_allowed") is True
        and git_state.get("push_origin_main_allowed") is True
    )
    if not is_linked_worktree and not bootstrap_allowed and not accepted_main_checkout:
        failures.append("Full ALE requires a linked worktree after bootstrap closes")
    return failures


def _unique(items: list[str]) -> list[str]:
    return list(dict.fromkeys(items))


def build_full_report(project_root: Path) -> dict[str, object]:
    root = project_root.resolve()
    failures: list[str] = []
    try:
        state = load_state(root / STATE_FILE)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        failures.append(f"unable to load {STATE_FILE}: {exc}")
        state = {}

    failures.extend(check_state_schema(state))
    failures.extend(check_authority_paths(state, root))
    failures.extend(check_document_consistency(state, root))
    failures.extend(check_git_consistency(state, root))
    failures.extend(check_worktree_consistency(state, root))
    failures = _unique(failures)
    return {
        "mode": FULL_ALE_MODE,
        "project_root": str(root),
        "passed": not failures,
        "failures": failures,
    }


def _normalize_allowed_file(value: str) -> tuple[str | None, str | None]:
    relative, error = _safe_relative_path(value)
    if error is not None or relative is None:
        return None, error
    return relative.as_posix(), None


def _is_expected_runtime_ignored(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized in {".DS_Store", "Thumbs.db", "config/local.yaml"}:
        return True
    if normalized.startswith(EXPECTED_RUNTIME_IGNORED_PREFIXES):
        return True
    if "/__pycache__/" in f"/{normalized}" or normalized.startswith("__pycache__/"):
        return True
    return normalized.lower().endswith(EXPECTED_RUNTIME_IGNORED_SUFFIXES)


def _changed_paths(root: Path, baseline: str) -> tuple[set[str], list[str]]:
    failures: list[str] = []
    commands = (
        ("committed", ("diff", "--name-only", f"{baseline}..HEAD", "--")),
        ("staged", ("diff", "--cached", "--name-only", "--")),
        ("unstaged", ("diff", "--name-only", "--")),
        ("untracked", ("ls-files", "--others", "--exclude-standard", "--")),
        (
            "ignored",
            ("ls-files", "--others", "--ignored", "--exclude-standard", "--"),
        ),
    )
    paths: set[str] = set()
    for label, args in commands:
        completed = _git(root, *args)
        if completed.returncode != 0:
            failures.append(f"unable to inspect {label} paths: {completed.stderr.strip()}")
            continue
        observed = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        if label == "ignored":
            observed = [item for item in observed if not _is_expected_runtime_ignored(item)]
        paths.update(observed)
    return paths, failures


def _diff_check_failures(root: Path, baseline: str) -> list[str]:
    failures: list[str] = []
    for label, args in (
        ("committed", ("diff", "--check", f"{baseline}..HEAD", "--")),
        ("staged", ("diff", "--cached", "--check", "--")),
        ("unstaged", ("diff", "--check", "--")),
    ):
        completed = _git(root, *args)
        if completed.returncode != 0:
            summary = completed.stdout.strip() or completed.stderr.strip()
            failures.append(f"{label} git diff --check failed: {summary}")
    return failures


def build_fast_report(
    project_root: Path,
    baseline_commit: str,
    authorized_work_branch: str,
    allowed_files: list[str],
) -> dict[str, object]:
    root = project_root.resolve()
    failures: list[str] = []
    allowed: list[str] = []
    for raw in allowed_files:
        normalized, error = _normalize_allowed_file(raw)
        if error is not None or normalized is None:
            failures.append(f"invalid allowed file {raw!r}: {error}")
        else:
            allowed.append(normalized)
    if not allowed_files:
        failures.append("Fast Loop requires at least one allowed file")
    if len(allowed) != len(set(allowed)):
        failures.append("Fast Loop allowed files must be unique")

    try:
        actual_root = Path(_git_text(root, "rev-parse", "--show-toplevel")).resolve()
        current_branch = _git_text(root, "branch", "--show-current")
    except subprocess.CalledProcessError:
        failures.append("project root is not a Git repository")
        actual_root = root
        current_branch = ""
    if actual_root != root:
        failures.append(f"Git root mismatch: expected {root}, got {actual_root}")
    if current_branch != authorized_work_branch:
        failures.append(
            f"current branch must be {authorized_work_branch}, got {current_branch}"
        )

    baseline = _git(root, "rev-parse", "--verify", f"{baseline_commit}^{{commit}}")
    if baseline.returncode != 0:
        failures.append(f"baseline commit is unavailable: {baseline_commit}")
    elif baseline.stdout.strip() != baseline_commit:
        failures.append("baseline_commit must be a full resolved commit SHA")
    else:
        if _git(root, "merge-base", "--is-ancestor", baseline_commit, "HEAD").returncode != 0:
            failures.append("baseline commit is not an ancestor of HEAD")
        for reference in ("refs/heads/main", "refs/remotes/origin/main"):
            resolved = _git(root, "rev-parse", "--verify", reference)
            if resolved.returncode != 0:
                failures.append(f"protected ref is missing: {reference}")
            elif resolved.stdout.strip() != baseline_commit:
                failures.append(f"protected ref moved: {reference}")

        observed, inspect_failures = _changed_paths(root, baseline_commit)
        failures.extend(inspect_failures)
        outside = sorted(observed - set(allowed))
        if outside:
            failures.append(f"out-of-scope paths detected: {', '.join(outside)}")
        failures.extend(_diff_check_failures(root, baseline_commit))

    failures = _unique(failures)
    return {
        "mode": FAST_LOOP_MODE,
        "project_root": str(root),
        "baseline_commit": baseline_commit,
        "authorized_work_branch": authorized_work_branch,
        "allowed_files": allowed,
        "passed": not failures,
        "failures": failures,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-only ALE project state checker")
    parser.add_argument(
        "--mode",
        choices=(FULL_ALE_MODE, FAST_LOOP_MODE),
        default=FULL_ALE_MODE,
    )
    parser.add_argument("--project-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--baseline-commit")
    parser.add_argument("--authorized-work-branch")
    parser.add_argument("--allowed-file", action="append", default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _format_text(report: dict[str, object]) -> str:
    if report["passed"]:
        return f"PASS {report['mode']}"
    failures = "\n".join(f"- {item}" for item in report["failures"])
    return f"FAIL {report['mode']}\n{failures}"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.mode == FULL_ALE_MODE:
        unexpected = args.baseline_commit or args.authorized_work_branch or args.allowed_file
        if unexpected:
            report: dict[str, object] = {
                "mode": FULL_ALE_MODE,
                "project_root": str(args.project_root.resolve()),
                "passed": False,
                "failures": ["Full ALE does not accept Fast Loop authority arguments"],
            }
        else:
            report = build_full_report(args.project_root)
    else:
        missing: list[str] = []
        if not args.baseline_commit:
            missing.append("--baseline-commit")
        if not args.authorized_work_branch:
            missing.append("--authorized-work-branch")
        if not args.allowed_file:
            missing.append("--allowed-file")
        if missing:
            report = {
                "mode": FAST_LOOP_MODE,
                "project_root": str(args.project_root.resolve()),
                "passed": False,
                "failures": [f"missing Fast Loop arguments: {', '.join(missing)}"],
            }
        else:
            report = build_fast_report(
                args.project_root,
                args.baseline_commit,
                args.authorized_work_branch,
                args.allowed_file,
            )

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        print(_format_text(report))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
