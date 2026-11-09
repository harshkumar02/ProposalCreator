from contextlib import nullcontext
from logging.config import fileConfig

from alembic import context

from app.core.database import Base, engine
import app.models.models  # noqa: F401 - registers tables on Base.metadata

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=str(engine.url),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=engine.dialect.name == "sqlite",
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # app.core.migrations passes its own connection; the CLI opens one.
    shared = config.attributes.get("connection")
    with nullcontext(shared) if shared is not None else engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite can't ALTER most things; batch mode rebuilds tables instead.
            render_as_batch=connection.dialect.name == "sqlite",
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
