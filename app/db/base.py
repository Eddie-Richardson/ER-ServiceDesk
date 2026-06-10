# ER-ServiceDesk/app/db/base.py
# SQLAlchemy Base class for ORM models
#
# This module defines the shared SQLAlchemy Base class used by all ORM models.
# Every model inherits from this Base so SQLAlchemy can track metadata,
# generate tables, and integrate with Alembic for migrations.
#
# IMPORTANT:
# This file MUST NOT import any models.
# Importing models here creates circular imports because models import Base.
#
# Alembic does NOT require model imports in this file.
# Alembic should import models through app/models/__init__.py instead.

from sqlalchemy.orm import declarative_base

# ---------------------------------------------------------------------------
# SQLAlchemy Declarative Base
# ---------------------------------------------------------------------------
# The declarative_base() function returns a base class that all ORM models
# must inherit from. It stores metadata about tables, columns, and mappings.
# Alembic uses this metadata during autogenerate operations.
Base = declarative_base()
