# ER-ServiceDesk/app/db/session.py
"""
SQLAlchemy engine and session factory used throughout the application.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """
    FastAPI dependency that yields a database session for a single request.

    Yields:
        A SQLAlchemy Session, closed automatically once the request finishes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
