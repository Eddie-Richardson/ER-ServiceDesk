# ER-ServiceDesk/app/db/session.py
# Database engine and session factory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Create SQLAlchemy engine using the configured database URL
engine = create_engine(settings.DATABASE_URL, future=True)

# Session factory for creating database sessions
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
