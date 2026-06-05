# ER-ServiceDesk/alembic_backup/env.py
# Alembic migration environment configuration
#
# This module configures and runs Alembic migrations for the ER‑ServiceDesk project.
# It sets up logging, injects the database URL, loads SQLAlchemy metadata, and
# determines whether migrations should run in offline or online mode.
#
# Alembic uses this file as the entry point for all migration operations.

from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

# Load application settings (provides DATABASE_URL for migrations)
from app.core.config import settings

# Import SQLAlchemy Base so Alembic can detect models for autogeneration
from app.db.base import Base

# ---------------------------------------------------------------------------
# Alembic configuration setup
# ---------------------------------------------------------------------------

# Alembic Config object (reads alembic_backup.ini and holds migration settings)
config = context.config

# Configure Python logging using alembic_backup.ini logging settings
fileConfig(config.config_file_name)

# Inject the actual database URL into Alembic's configuration
# This ensures migrations always target the correct environment database
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Metadata used by Alembic for autogenerate (reflects all SQLAlchemy models)
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migration runner
# ---------------------------------------------------------------------------
def run_migrations_offline():
    """
    Run migrations in 'offline' mode.

    Offline mode generates SQL migration scripts without connecting to the
    database. Alembic writes SQL statements directly to the output stream.
    Useful for environments where direct DB access is restricted.
    """
    context.configure(
        url=settings.DATABASE_URL,        # Database URL for script generation
        target_metadata=target_metadata,  # Model metadata for autogenerate
        literal_binds=True,               # Render values directly into SQL
    )

    # Begin a migration transaction and emit SQL to the output
    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migration runner
# ---------------------------------------------------------------------------
def run_migrations_online():
    """
    Run migrations in 'online' mode.

    Online mode creates a real database connection and applies migrations
    directly to the target database. This is the standard mode for development
    and production environments.
    """
    # Create a SQLAlchemy engine using Alembic configuration
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),  # Load DB settings
        prefix="sqlalchemy.",                           # Config key prefix
        poolclass=pool.NullPool,                        # No connection pooling
    )

    # Establish a DB connection and run migrations against it
    with connectable.connect() as connection:
        context.configure(
            connection=connection,           # Active DB connection
            target_metadata=target_metadata  # Model metadata for autogenerate
        )

        # Execute migrations inside a transaction block
        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Migration mode selector
# ---------------------------------------------------------------------------
# Alembic determines whether to run in offline or online mode based on CLI flags.
# This block dispatches to the correct migration runner.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
