import logging
from logging.handlers import RotatingFileHandler

from app.core.config import AppSettings


def configure_logging(settings: AppSettings) -> None:
    log_dir = settings.storage.logs_dir
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if log_dir is not None:
        handlers.append(
            RotatingFileHandler(
                log_dir / settings.logging.file_name,
                maxBytes=5 * 1024 * 1024,
                backupCount=5,
                encoding="utf-8",
            )
        )

    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
        force=True,
    )
