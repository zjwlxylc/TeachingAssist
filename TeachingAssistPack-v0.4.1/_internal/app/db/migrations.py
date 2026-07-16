import logging
from pathlib import Path

from app.db.session import get_connection


logger = logging.getLogger(__name__)
MIGRATIONS_DIR = Path(__file__).parent / "migrations"


def ensure_schema_table() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


def applied_versions() -> set[str]:
    with get_connection() as connection:
        rows = connection.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def run_migrations() -> list[str]:
    ensure_schema_table()
    applied = applied_versions()
    executed: list[str] = []

    for migration_file in sorted(MIGRATIONS_DIR.glob("*.sql")):
        version = migration_file.stem
        if version in applied:
            continue

        sql = migration_file.read_text(encoding="utf-8")
        with get_connection() as connection:
            connection.executescript(sql)
            connection.execute("INSERT INTO schema_migrations(version) VALUES (?)", (version,))
        executed.append(version)
        logger.info("Applied database migration %s", version)

    return executed


def integrity_check() -> str:
    with get_connection() as connection:
        row = connection.execute("PRAGMA integrity_check").fetchone()
    return str(row[0]) if row else "unknown"
