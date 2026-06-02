# ER-ServiceDesk/alembic/env.py
# Alembic migration environment configuration

# Alembic environment configuration for ER‑ServiceDesk migrations

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Load application settings (DATABASE_URL)
from app.core.config import settings

# Import Base so Alembic can autogenerate migrations from models
from app.db.base import Base

# Alembic Config object (reads alembic.ini)
config = context.config

# Configure Python logging based on alembic.ini
fileConfig(config.config_file_name)

# Inject the actual database URL into Alembic config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Metadata for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline():
    """
    Run migrations in 'offline' mode.
    This configures Alembic to generate SQL scripts without connecting
    to the actual database.
    """
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """
    Run migrations in 'online' mode.
    This creates a real database connection and applies migrations directly.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    # Connect and run migrations
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


# Determine mode and execute the appropriate migration runner
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
