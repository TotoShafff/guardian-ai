"""Alembic migration environment for the Guardian AI backend.

Wires Alembic to the project's own configuration and SQLAlchemy metadata
instead of relying on static values in `alembic.ini`:

- The database URL is read from `app.config.get_settings()`, so it always
  matches what the running application uses and no credentials are
  hardcoded in `alembic.ini`.
- `target_metadata` is `Base.metadata` from `app.persistence.database`,
  populated by importing every module in `app.persistence.models` so all
  ORM tables are registered before Alembic inspects the metadata.
"""

import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# alembic/env.py -> apps/backend is one level up. Alembic's own sys.path
# handling (`prepend_sys_path`) depends on the current working directory,
# so this makes `import app...` reliable regardless of where Alembic is
# invoked from.
_BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from app.config import get_settings  # noqa: E402
from app.persistence.database import Base  # noqa: E402
from app.persistence import models  # noqa: E402,F401  (registers all tables on Base.metadata)

# This is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The application's own settings are the single source of truth for the
# database URL; this overrides whatever (empty) placeholder is in alembic.ini.
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# All ORM models defined in `app.persistence.models` share `Base`, so its
# metadata is the complete target schema for autogenerate and migrations.
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though
    an Engine is acceptable here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script
    output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        transaction_per_migration=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            transaction_per_migration=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
