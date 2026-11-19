"""
Bring the database schema up to date with Alembic.

    python -m app.db.migrate          # upgrade to the latest revision

Databases created before migrations existed (by ``Base.metadata.create_all``) have
every table but no ``alembic_version``; they are stamped at the initial revision
first, so only the later migrations run.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.core.config import settings

BACKEND_DIR = Path(__file__).resolve().parents[2]
INITIAL_REVISION = "0001"


def _config(database_url: str) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = database_url
    cfg.attributes["configure_logging"] = False
    return cfg


def upgrade_database(database_url: str | None = None) -> None:
    url = database_url or settings.database_sync_url
    engine = create_engine(url)
    try:
        tables = set(inspect(engine).get_table_names())
    finally:
        engine.dispose()

    cfg = _config(url)
    if tables and "alembic_version" not in tables:
        command.stamp(cfg, INITIAL_REVISION)
    command.upgrade(cfg, "head")


if __name__ == "__main__":
    upgrade_database()
    print("Database schema is up to date.")
