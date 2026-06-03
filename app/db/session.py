# ER-ServiceDesk/app/db/session.py
# Database engine and session factory
#
# This module initializes the SQLAlchemy engine and session factory used
# throughout the ER‑ServiceDesk application. It provides the core database
# connection infrastructure, allowing the rest of the system to create
# sessions for executing queries and transactions.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# ---------------------------------------------------------------------------
# SQLAlchemy Engine
# ---------------------------------------------------------------------------
# The engine manages the connection to the database. It is created using the
# DATABASE_URL loaded from environment variables. `future=True` enables the
# SQLAlchemy 2.0‑style engine behavior.
engine = create_engine(
    settings.DATABASE_URL,
    future=True
)

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
# SessionLocal is a sessionmaker instance that creates new SQLAlchemy Session
# objects. These sessions are used for all ORM interactions within the app.
# - autocommit=False ensures explicit transaction control
# - autoflush=False prevents automatic flushes before queries
# - bind=engine attaches the session to the configured database engine
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
