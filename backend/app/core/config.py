from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOCAL_ROOT = Path("C:/TeachingAssist")


class ServerSettings(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8080
    fallback_ports: list[int] = Field(default_factory=lambda: [8081, 8888])
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])


class StorageSettings(BaseModel):
    local_root: Path = DEFAULT_LOCAL_ROOT
    database_path: Path | None = None
    uploads_dir: Path | None = None
    backups_dir: Path | None = None
    logs_dir: Path | None = None
    runtime_dir: Path | None = None
    removable_root: Path | None = None


class LoggingSettings(BaseModel):
    level: str = "INFO"
    file_name: str = "teaching_assist.log"


class AppSettings(BaseModel):
    app_name: str = "大学教学过程辅助软件"
    environment: str = "development"
    api_prefix: str = "/api/v1"
    server: ServerSettings = Field(default_factory=ServerSettings)
    storage: StorageSettings = Field(default_factory=StorageSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    def normalized(self) -> "AppSettings":
        storage = self.storage
        local_root = storage.local_root
        self.storage.database_path = storage.database_path or local_root / "data" / "teaching_assist.db"
        self.storage.uploads_dir = storage.uploads_dir or local_root / "uploads"
        self.storage.backups_dir = storage.backups_dir or local_root / "backups"
        self.storage.logs_dir = storage.logs_dir or local_root / "logs"
        self.storage.runtime_dir = storage.runtime_dir or local_root / "runtime"
        return self


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")
    return data


@lru_cache
def get_settings() -> AppSettings:
    default_config = PROJECT_ROOT / "config" / "default.yaml"
    local_config = PROJECT_ROOT / "config" / "local.yaml"
    raw = _deep_merge(_load_yaml(default_config), _load_yaml(local_config))
    return AppSettings.model_validate(raw).normalized()
