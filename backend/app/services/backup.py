import shutil
import sqlite3
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.session import get_connection, get_database_path
from app.services.startup import detect_removable_root


BACKUP_KEEP_COUNT = 5


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _record_backup(backup_type: str, target: str, path: Path, status: str, message: str = "") -> None:
    file_size = path.stat().st_size if path.exists() else 0
    with get_connection() as connection:
        connection.execute(
            """
            INSERT INTO backup_records(backup_type, target, file_path, file_size, status, message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (backup_type, target, str(path), file_size, status, message),
        )


def _backup_targets() -> list[tuple[str, Path]]:
    settings = get_settings()
    targets: list[tuple[str, Path]] = []
    if settings.storage.backups_dir:
        targets.append(("local", settings.storage.backups_dir))
    removable_root = detect_removable_root(settings)
    if removable_root:
        targets.append(("removable", removable_root / "backup"))
    return targets


def create_backup(backup_type: str = "manual") -> list[dict[str, object]]:
    source = get_database_path()
    if not source.exists():
        raise AppError("数据库文件不存在，无法备份", code="DATABASE_NOT_FOUND")

    results: list[dict[str, object]] = []
    for target_name, target_dir in _backup_targets():
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"teaching_assist_{backup_type}_{_timestamp()}.db"
        source_connection = None
        target_connection = None
        try:
            source_connection = sqlite3.connect(source)
            target_connection = sqlite3.connect(target_path)
            source_connection.backup(target_connection)
            _record_backup(backup_type, target_name, target_path, "success")
            _cleanup_old_backups(target_dir)
            results.append(
                {
                    "target": target_name,
                    "file_path": str(target_path),
                    "file_size": target_path.stat().st_size,
                    "status": "success",
                }
            )
        except Exception as exc:
            _record_backup(backup_type, target_name, target_path, "failed", str(exc))
            results.append({"target": target_name, "file_path": str(target_path), "status": "failed", "message": str(exc)})
        finally:
            if target_connection:
                target_connection.close()
            if source_connection:
                source_connection.close()
    return results


def _cleanup_old_backups(target_dir: Path) -> None:
    backups = sorted(target_dir.glob("teaching_assist_*.db"), key=lambda path: path.stat().st_mtime, reverse=True)
    for stale in backups[BACKUP_KEEP_COUNT:]:
        stale.unlink(missing_ok=True)


def list_backups() -> list[dict[str, object]]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, backup_type, target, file_path, file_size, status, message, created_at
            FROM backup_records
            ORDER BY created_at DESC, id DESC
            LIMIT 50
            """
        ).fetchall()
    return [dict(row) for row in rows]


def restore_backup(file_path: str) -> dict[str, object]:
    source = Path(file_path).resolve()
    if not source.exists() or source.suffix.lower() != ".db":
        raise AppError("备份文件不存在或格式不正确", code="BACKUP_NOT_FOUND")

    # Prevent path traversal: only allow restoring from known backup directories
    settings = get_settings()
    allowed_dirs: list[Path] = []
    if settings.storage.backups_dir:
        allowed_dirs.append(settings.storage.backups_dir.resolve())
    removable_root = detect_removable_root(settings)
    if removable_root:
        allowed_dirs.append((removable_root / "backup").resolve())
    if not any(source == allowed or allowed in source.parents for allowed in allowed_dirs):
        raise AppError("备份文件不在允许的目录范围内", code="BACKUP_PATH_NOT_ALLOWED")

    database_path = get_database_path()
    safety_dir = get_settings().storage.backups_dir
    if safety_dir is None:
        raise AppError("本地备份目录未配置", code="BACKUP_DIR_NOT_CONFIGURED")
    safety_dir.mkdir(parents=True, exist_ok=True)
    safety_backup = safety_dir / f"before_restore_{_timestamp()}.db"
    if database_path.exists():
        shutil.copy2(database_path, safety_backup)
        _record_backup("before_restore", "local", safety_backup, "success")

    shutil.copy2(source, database_path)
    return {"restored_from": str(source), "safety_backup": str(safety_backup)}
