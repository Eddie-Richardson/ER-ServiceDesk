# ER-ServiceDesk/app/db/base.py
# SQLAlchemy Base class for ORM models

from sqlalchemy.orm import declarative_base

# Base class used by all SQLAlchemy models in the project
Base = declarative_base()
