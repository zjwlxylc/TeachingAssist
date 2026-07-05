import logging
from pathlib import Path

from app.core.config import AppSettings
from app.db.migrations import integrity_check, run_migrations


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

    if integrity.lower() != "ok":
        logger.error("SQLite integrity check failed: %s", integrity)
    else:
        logger.info("SQLite integrity check passed")

    return {
        "directories": [str(path) for path in directories],
        "database_path": str(settings.storage.database_path),
        "migrations": migrations,
        "integrity": integrity,
        "removable_root": str(removable_root) if removable_root else None,
    }
