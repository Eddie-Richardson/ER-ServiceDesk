# ER-ServiceDesk/tests/test_auth.py
# Tests for login and route-level auth enforcement.
"""
Covers: successful/failed login, unauthenticated access being rejected,
and the admin-only vs any-staff route split enforced via
get_current_user / require_superuser.
"""

from app.core.security import hash_password
from app.models.user import User


def _create_login_user(db, email, password, is_superuser=False):
    user = User(
        email=email,
        hashed_password=hash_password(password),
        first_name="Login",
        last_name="Test",
        is_active=True,
        is_superuser=is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_login_success(client, db):
    """A correct email/password pair returns a bearer token."""
    _create_login_user(db, "login_ok@example.com", "Correct-Password123!")

    response = client.post(
        "/auth/login",
        json={"email": "login_ok@example.com", "password": "Correct-Password123!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password(client, db):
    """An incorrect password is rejected with 400, not a 500 or a token."""
    _create_login_user(db, "login_wrong@example.com", "Correct-Password123!")

    response = client.post(
        "/auth/login",
        json={"email": "login_wrong@example.com", "password": "wrong-password"},
    )

    assert response.status_code == 400
    assert "access_token" not in response.json()


def test_login_nonexistent_user(client, db):
    """Logging in as a user that doesn't exist fails the same way as a wrong password."""
    response = client.post(
        "/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert response.status_code == 400


def test_protected_route_requires_token(client):
    """Hitting a staff-only route with no Authorization header is rejected."""
    response = client.get("/tickets/")
    assert response.status_code == 401


def test_protected_route_rejects_garbage_token(client):
    """A malformed/garbage bearer token is rejected, not silently accepted."""
    response = client.get("/tickets/", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_agent_can_access_staff_route(client, agent_headers):
    """A regular (non-superuser) authenticated user can hit staff-level routes."""
    response = client.get("/tickets/", headers=agent_headers)
    assert response.status_code == 200


def test_agent_cannot_access_admin_route(client, agent_headers):
    """A regular (non-superuser) authenticated user is rejected from admin-only routes."""
    response = client.get("/users/", headers=agent_headers)
    assert response.status_code == 403


def test_superuser_can_access_admin_route(client, superuser_headers):
    """A superuser can access admin-only routes like user management."""
    response = client.get("/users/", headers=superuser_headers)
    assert response.status_code == 200
