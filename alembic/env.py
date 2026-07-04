from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.database.models import Base
from app.database.session import _normalise_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _configured_url() -> str:
    x_arguments = context.get_x_argument(as_dictionary=True)
    url = x_arguments.get("database_url")
    if not url:
        raise RuntimeError(
            "Alembic requires an explicit database URL. "
            "Run with -x database_url=$env:TEST_DATABASE_URL for verification."
        )
    if "USER:PASSWORD@HOST/DBNAME" in url or "TEST_HOST/TEST_DBNAME" in url:
        raise RuntimeError("Refusing to run Alembic with placeholder database URL")
    return _normalise_database_url(url)


def run_migrations_offline() -> None:
    context.configure(
        url=_configured_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _configured_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
