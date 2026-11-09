"""Apply Alembic migrations at startup.

Databases created before Alembic was introduced (by the old
``Base.metadata.create_all``) have tables but no ``alembic_version`` row. Those
are stamped at the baseline revision first, so ``upgrade`` only applies what
came after it instead of failing on "table already exists".
"""
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine

log = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
BASELINE_REVISION = "0001"


def run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["configure_logger"] = False

    with engine.begin() as connection:
        cfg.attributes["connection"] = connection
        tables = set(inspect(connection).get_table_names())
        if tables and "alembic_version" not in tables:
            log.warning(
                "Pre-Alembic database detected; stamping it at baseline %s. "
                "If it predates the current models, delete it and restart.",
                BASELINE_REVISION,
            )
            command.stamp(cfg, BASELINE_REVISION)
        command.upgrade(cfg, "head")
