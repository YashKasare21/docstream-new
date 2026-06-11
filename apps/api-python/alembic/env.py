"""Alembic environment configuration for DocStream API.

Uses the project's ``Base.metadata`` and ``JOBS_DB_URL`` so migrations
stay in sync with the ORM models.
"""

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Alembic Config object
config = context.config

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── DocStream-specific imports ────────────────────────────────────────────────
# Import Base so autogenerate can detect model changes.
from docstream_api.database import JOBS_DB_URL  # noqa: E402
from docstream_api.db_models import Base  # noqa: E402

target_metadata = Base.metadata

# Override the sqlalchemy.url from alembic.ini with our project's DB URL.
config.set_main_option("sqlalchemy.url", JOBS_DB_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (connect to the live DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
