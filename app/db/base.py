# ER-ServiceDesk/app/db/base.py
# SQLAlchemy Base class for ORM models
#
# This module defines the shared SQLAlchemy Base class used by all ORM models
# in the ER‑ServiceDesk application. Every model inherits from this Base so
# that SQLAlchemy can track metadata, generate tables, and integrate with
# Alembic for migrations.

from sqlalchemy.orm import declarative_base

# ---------------------------------------------------------------------------
# SQLAlchemy Declarative Base
# ---------------------------------------------------------------------------
# The declarative_base() function returns a base class that all ORM models
# must inherit from. It stores metadata about tables, columns, and mappings.
# Alembic uses this metadata during autogenerate operations.
Base = declarative_base()
