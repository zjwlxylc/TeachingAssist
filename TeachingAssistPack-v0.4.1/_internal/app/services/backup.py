import os
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError
from app.db.session import get_connection, get_database_path
from app.services.startup import detect_removable_root


BACKUP_KEEP_COUNT = 5


def _timestamp() -> str:
    # 加入微秒与短 uuid 后缀，避免同一秒内多次备份（手动+自动）文件名冲突互相覆盖。
    return datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]


def _verify_sqlite_integrity(path: Path) -> None:
    """以只读方式校验 SQLite 文件完整性，损坏则拒绝使用（不污染线上库）。"""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise AppError(f"备份文件无法打开或不是有效的 SQLite 数据库: {exc}", code="BACKUP_INVALID", status_code=422)
    try:
        rows = conn.execute("PRAGMA integrity_check").fetchall()
        status = [row[0] for row in rows]
    except sqlite3.Error as exc:
        conn.close()
        raise AppError(f"备份文件完整性校验失败: {exc}", code="BACKUP_INTEGRITY_FAILED", status_code=422)
    finally:
        conn.close()
    if status != ["ok"]:
        raise AppError("备份文件完整性校验未通过，已拒绝恢复以防数据损坏", code="BACKUP_INTEGRITY_FAILED", status_code=422)


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

    # 恢复前先做完整性校验：损坏的备份一旦覆盖线上库，会导致全站查询崩溃。
    _verify_sqlite_integrity(source)

    safety_dir = get_settings().storage.backups_dir
    if safety_dir is None:
        raise AppError("本地备份目录未配置", code="BACKUP_DIR_NOT_CONFIGURED")
    safety_dir.mkdir(parents=True, exist_ok=True)
    safety_backup = safety_dir / f"before_restore_{_timestamp()}.db"
    if database_path.exists():
        shutil.copy2(database_path, safety_backup)
        _record_backup("before_restore", "local", safety_backup, "success")

    # 原子替换：先拷到同目录临时文件，再用 os.replace 一次性换入，
    # 避免直接覆盖正在被服务打开的库文件时出现半写状态。
    # 注意：若服务正在运行并持有 WAL 连接，仍建议先停止服务再恢复。
    temp_path = database_path.parent / f".restore_tmp_{uuid.uuid4().hex}.db"
    try:
        shutil.copy2(source, temp_path)
        os.replace(temp_path, database_path)
    finally:
        temp_path.unlink(missing_ok=True)
    return {"restored_from": str(source), "safety_backup": str(safety_backup)}
