# ER-ServiceDesk/tests/conftest.py
# Shared pytest fixtures for the whole test suite.
"""
Provides a real Postgres-backed test database (separate from the dev
database), a FastAPI TestClient wired to use it instead of the real DB,
and helper fixtures for creating authenticated superuser/agent requests.

Requires TEST_DATABASE_URL in the environment (see .env.example), pointing
at a separate database on the same Postgres instance used for development
-- never point this at your real dev/prod database, since tables are
dropped and recreated for every test run.
"""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.core.security import create_access_token, hash_password
from app.models.user import User
from app.models.role import Role
from app.models.user_role import UserRole

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg2://postgres:postgres@db:5432/erservicedesk_test",
)

engine = create_engine(TEST_DATABASE_URL, future=True)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_schema():
    """
    Create every table once for the test session, drop them all afterward.

    Session-scoped so table creation only happens once per test run rather
    than once per test, which would be slow given the size of this schema.
    """
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    """
    Truncate every table between tests so each test starts from a blank
    slate, without paying the cost of recreating the schema every time.
    """
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


@pytest.fixture
def db():
    """Yield a SQLAlchemy session bound to the test database."""
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db):
    """
    Yield a FastAPI TestClient with `get_db` overridden to use the test
    database instead of the real one.
    """
    def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _make_user(db, email: str, is_superuser: bool) -> User:
    """Create and persist a bare User for auth-related fixtures."""
    user = User(
        email=email,
        hashed_password=hash_password("Testpass123!"),
        first_name="Test",
        last_name="User",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def superuser_headers(db):
    """
    Create a superuser and return an Authorization header dict for it.

    Use this in tests that need admin-only routes to succeed.
    """
    user = _make_user(db, "admin_test@example.com", is_superuser=True)
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def agent_headers(db):
    """
    Create a non-superuser (regular staff) user and return an
    Authorization header dict for it.

    Use this in tests that need standard authenticated access but should
    be rejected from admin-only routes.
    """
    user = _make_user(db, "agent_test@example.com", is_superuser=False)
    token = create_access_token({"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}
