# ER-ServiceDesk/app/db/base.py
# SQLAlchemy Base class for ORM models
"""
Shared SQLAlchemy declarative Base used by every ORM model.

IMPORTANT: this file must NOT import any models -- doing so creates
circular imports, since models import Base from here. Alembic imports
models separately via app/models/__init__.py.
"""

from sqlalchemy.orm import declarative_base

Base = declarative_base()
