"""Alembic environment - configured for the app's async SQLAlchemy engine."""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

import app.models  # noqa: F401 - ensures every model is registered before autogenerate
from app.core.config import get_settings
from app.db.session import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

settings = get_settings()
# Online mode uses the async driver (postgresql+asyncpg).
config.set_main_option("sqlalchemy.url", settings.database_url)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    # Offline mode generates SQL without a live connection; use the sync URL
    # so that alembic can parse the dialect correctly without asyncpg.
    url = settings.database_url_sync
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def _ensure_wide_version_table(connection) -> None:  # noqa: ANN001
    """Alembic's default `alembic_version.version_num` column is
    VARCHAR(32), which is too narrow for several of this project's
    descriptive revision IDs (e.g. '0007_evidence_technology_jobs_fields'
    is 36 characters, '0005_company_profile_signal_source' is 34) -
    without this, a fresh `alembic upgrade head` fails partway through
    with a string-data-right-truncation error the first time it tries to
    record one of those revisions.

    Alembic only creates `alembic_version` if it's missing, so
    pre-creating it here with a wide column - or widening an
    already-existing narrow one left over from a database that's only
    partially migrated - means Alembic's own bookkeeping just uses it
    as-is. Idempotent: safe to run on every invocation, on any database
    state (missing table, narrow table, or already-wide table).
    """
    connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(255) NOT NULL, "
            "CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)"
            ")"
        )
    )
    connection.execute(text("ALTER TABLE alembic_version ALTER COLUMN version_num TYPE VARCHAR(255)"))


def do_run_migrations(connection) -> None:  # noqa: ANN001
    _ensure_wide_version_table(connection)
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        # AsyncConnection auto-begins a transaction on first execute but
        # does NOT auto-commit on context-manager exit - without this,
        # every migration below silently rolls back when the connection
        # closes, even though Alembic logs "Running upgrade ..." for each
        # one as if it succeeded. This was the actual cause of migrations
        # never landing on a real database.
        await connection.commit()
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
