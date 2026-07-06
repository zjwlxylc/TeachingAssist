import asyncio
import logging
from pathlib import Path

from app.core.config import AppSettings
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


def detect_removable_root(settings: AppSettings) -> Path | None:
    if settings.storage.removable_root and settings.storage.removable_root.exists():
        return settings.storage.removable_root

    project_drive = Path(__file__).resolve().anchor
    candidate = Path(project_drive)
    return candidate if candidate.exists() else None


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
