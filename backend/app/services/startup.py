import asyncio
import ctypes
import logging
import sys
from ctypes import wintypes
from pathlib import Path

from app.core.config import AppSettings, PROJECT_ROOT
from app.db.migrations import integrity_check, run_migrations
from app.services.ai import check_connectivity, get_ai_overview


logger = logging.getLogger(__name__)


def initialize_directories(settings: AppSettings) -> list[Path]:
    paths = [
        settings.storage.database_path.parent if settings.storage.database_path else None,
        settings.storage.uploads_dir,
        settings.storage.backups_dir,
        settings.storage.logs_dir,
        settings.storage.runtime_dir,
    ]
    created: list[Path] = []
    for path in paths:
        if path is None:
            continue
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
    return created


def _windows_removable_drives() -> list[str]:
    """Return root paths (e.g. 'E:\\') of removable drives on Windows."""
    if sys.platform != "win32":
        return []
    try:
        kernel32 = ctypes.windll.kernel32
    except AttributeError:
        return []
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH + 1)
    length = kernel32.GetLogicalDriveStringsW(wintypes.MAX_PATH, buf)
    if not length:
        return []
    drives = [buf[i : i + 3] for i in range(0, length, 4)]
    removable: list[str] = []
    for drive in drives:
        if not drive.endswith("\\"):
            continue
        try:
            if kernel32.GetDriveTypeW(drive) == 2:  # DRIVE_REMOVABLE
                removable.append(drive)
        except OSError:
            continue
    return removable


def _is_removable_drive(drive_root: str) -> bool:
    if sys.platform != "win32":
        return False
    try:
        return ctypes.windll.kernel32.GetDriveTypeW(drive_root) == 2
    except (AttributeError, OSError):
        return False


def detect_removable_root(settings: AppSettings) -> Path | None:
    configured = settings.storage.removable_root
    if configured is not None:
        # Resolve relative paths (e.g. ".") against the install location so a
        # literal "." never leaks into the report.
        if configured.is_absolute():
            configured = configured.resolve()
        else:
            configured = (PROJECT_ROOT / configured).resolve()
        if configured.exists():
            return configured

    # Auto-detect: prefer the drive that actually hosts the running program
    # (reliable in both frozen and source mode, unlike __file__ which points
    # into PyInstaller's temp extraction dir), otherwise scan removable drives.
    exe_drive = Path(sys.executable).resolve().anchor
    if _is_removable_drive(exe_drive):
        return Path(exe_drive)
    removable = _windows_removable_drives()
    if removable:
        return Path(removable[0])
    return None


def run_startup_checks(settings: AppSettings) -> dict[str, object]:
    directories = initialize_directories(settings)
    migrations = run_migrations()
    integrity = integrity_check()
    removable_root = detect_removable_root(settings)
    ai_status: dict[str, object]

    if integrity.lower() != "ok":
        logger.error("SQLite integrity check failed: %s", integrity)
    else:
        logger.info("SQLite integrity check passed")

    try:
        overview = get_ai_overview()
        if overview.get("active_provider"):
            ai_status = check_connectivity()
        else:
            ai_status = {
                "status": "disabled",
                "message": "未配置 AI Provider，系统进入基础模式",
                "basic_mode": True,
            }
    except Exception as exc:
        logger.warning("AI startup connectivity check skipped: %s", exc)
        ai_status = {
            "status": "unavailable",
            "message": "AI 启动自检失败，系统进入基础模式",
            "basic_mode": True,
        }

    return {
        "directories": [str(path) for path in directories],
        "database_path": str(settings.storage.database_path),
        "migrations": migrations,
        "integrity": integrity,
        "removable_root": str(removable_root) if removable_root else None,
        "ai": ai_status,
    }


async def auto_backup_worker(interval_seconds: int = 900) -> None:
    from app.services.backup import create_backup

    while True:
        await asyncio.sleep(interval_seconds)
        try:
            create_backup("auto")
            logger.info("Automatic database backup completed")
        except Exception:
            logger.exception("Automatic database backup failed")
