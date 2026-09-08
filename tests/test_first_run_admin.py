# ER-ServiceDesk/tests/test_first_run_admin.py
"""
Covers the first-run admin account creation flow -- the only way into
a fresh install now that seed.py creates zero default accounts.

Two layers: UserService.any_exist()/create_first_run_admin() directly
(service-layer), and the genuinely unauthenticated
GET /users/first-run-status / POST /users/first-run-admin endpoints
via the real HTTP client, confirming no token is required to reach
either one -- that's the entire point of this flow.
"""

from app.services.user_service import user_service
from app.schemas.user import FirstRunAdminCreate
from app.models.user import User


def test_any_exist_false_on_a_fresh_database(db):
    """A genuinely empty user table reports no account exists yet."""
    assert user_service.any_exist(db) is False


def test_any_exist_true_once_an_account_exists(db):
    """Once any account exists at all, any_exist() reflects that."""
    user_service.create_first_run_admin(db, FirstRunAdminCreate(
        email="admin@myrealshop.com", first_name="Eddie", last_name="Richardson",
        password="RealPassword1!",
    ))
    assert user_service.any_exist(db) is True


def test_create_first_run_admin_creates_a_real_superuser(db):
    """The created account is genuinely a superuser, active, and doesn't require a forced password change -- the person just chose their own real password directly."""
    created = user_service.create_first_run_admin(db, FirstRunAdminCreate(
        email="admin@myrealshop.com", first_name="Eddie", last_name="Richardson",
        password="RealPassword1!",
    ))
    assert created.is_superuser is True
    assert created.is_active is True
    assert created.must_change_password is False
    assert created.email == "admin@myrealshop.com"

    db_user = db.query(User).filter(User.id == created.id).first()
    assert db_user is not None
    assert db_user.hashed_password != "RealPassword1!"  # genuinely hashed, not stored as plaintext


def test_create_first_run_admin_rejects_a_weak_password(db):
    """A password that fails hash_password()'s own strength check is rejected with a clear message, and no account is created."""
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        user_service.create_first_run_admin(db, FirstRunAdminCreate(
            email="admin@myrealshop.com", first_name="Eddie", last_name="Richardson",
            password="weak",
        ))
    assert exc_info.value.status_code == 400
    assert user_service.any_exist(db) is False


def test_create_first_run_admin_rejects_a_second_attempt_once_an_account_exists(db):
    """
    Genuinely re-checks at the moment of creation, not just trusting
    an earlier any_exist() check -- the real safety net against a
    race between two people reaching this screen at once.
    """
    import pytest
    from fastapi import HTTPException

    user_service.create_first_run_admin(db, FirstRunAdminCreate(
        email="admin@myrealshop.com", first_name="Eddie", last_name="Richardson",
        password="RealPassword1!",
    ))

    with pytest.raises(HTTPException) as exc_info:
        user_service.create_first_run_admin(db, FirstRunAdminCreate(
            email="someone_else@myrealshop.com", first_name="Someone", last_name="Else",
            password="AnotherPassword1!",
        ))
    assert exc_info.value.status_code == 400

    # Confirm the original account is untouched, and no second one was created.
    remaining = db.query(User).all()
    assert len(remaining) == 1
    assert remaining[0].email == "admin@myrealshop.com"


def test_first_run_status_endpoint_requires_no_authentication(client):
    """GET /users/first-run-status is genuinely reachable with no Authorization header at all -- the whole point is checking this before any login is possible."""
    response = client.get("/users/first-run-status")
    assert response.status_code == 200
    assert response.json() == {"any_exist": False}


def test_first_run_status_endpoint_reflects_a_real_account(client, db):
    """Once a real account exists, the endpoint genuinely reports it, still with no authentication."""
    user_service.create_first_run_admin(db, FirstRunAdminCreate(
        email="admin@myrealshop.com", first_name="Eddie", last_name="Richardson",
        password="RealPassword1!",
    ))
    response = client.get("/users/first-run-status")
    assert response.status_code == 200
    assert response.json() == {"any_exist": True}


def test_first_run_admin_endpoint_requires_no_authentication(client):
    """POST /users/first-run-admin is genuinely reachable with no Authorization header at all, and genuinely creates a real account."""
    response = client.post("/users/first-run-admin", json={
        "email": "admin@myrealshop.com", "first_name": "Eddie", "last_name": "Richardson",
        "password": "RealPassword1!",
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["email"] == "admin@myrealshop.com"
    assert body["is_superuser"] is True


def test_first_run_admin_endpoint_rejects_once_an_account_already_exists(client):
    """A second call, over HTTP, is genuinely rejected once any account exists -- confirms the real safety check applies at the actual API surface, not just the service layer in isolation."""
    first = client.post("/users/first-run-admin", json={
        "email": "admin@myrealshop.com", "first_name": "Eddie", "last_name": "Richardson",
        "password": "RealPassword1!",
    })
    assert first.status_code == 200, first.text

    second = client.post("/users/first-run-admin", json={
        "email": "someone_else@myrealshop.com", "first_name": "Someone", "last_name": "Else",
        "password": "AnotherPassword1!",
    })
    assert second.status_code == 400
