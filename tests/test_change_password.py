# ER-ServiceDesk/tests/test_change_password.py
"""
Covers POST /auth/change-password -- genuinely, entirely untested
before this. The self-service password change flow for an account
whose password was set by an admin (must_change_password=True), which
has no access token yet -- this endpoint's whole reason to exist is
being reachable without one.
"""

from app.core.security import verify_password
from tests.factories import make_plain_user


def test_reachable_with_no_authorization_header_at_all(client, db):
    """The entire point of this endpoint -- someone with a temp password has no token yet. No Authorization header is passed here at all."""
    user = make_plain_user(db)
    response = client.post("/auth/change-password", json={
        "email": user.email, "current_password": "Irrelevant123!", "new_password": "MyOwnNewPassword1!",
    })
    assert response.status_code == 200


def test_a_correct_change_clears_must_change_password_and_hashes_the_new_password(client, db):
    user = make_plain_user(db)
    user.must_change_password = True
    db.commit()

    response = client.post("/auth/change-password", json={
        "email": user.email, "current_password": "Irrelevant123!", "new_password": "MyOwnNewPassword1!",
    })
    assert response.status_code == 200

    db.refresh(user)
    assert user.must_change_password is False
    assert verify_password("MyOwnNewPassword1!", user.hashed_password)


def test_rejects_the_wrong_current_password(client, db):
    user = make_plain_user(db)
    original_hash = user.hashed_password

    response = client.post("/auth/change-password", json={
        "email": user.email, "current_password": "TotallyWrongPassword!", "new_password": "MyOwnNewPassword1!",
    })
    assert response.status_code == 400

    db.refresh(user)
    assert user.hashed_password == original_hash


def test_rejects_a_new_password_that_fails_strength_validation(client, db):
    user = make_plain_user(db)
    original_hash = user.hashed_password

    response = client.post("/auth/change-password", json={
        "email": user.email, "current_password": "Irrelevant123!", "new_password": "weak",
    })
    assert response.status_code == 400

    db.refresh(user)
    assert user.hashed_password == original_hash


def test_returns_a_real_token_that_genuinely_works_for_a_follow_up_request(client, db):
    """The person ends up genuinely signed in immediately, not needing to log in again right after changing their password."""
    user = make_plain_user(db)
    response = client.post("/auth/change-password", json={
        "email": user.email, "current_password": "Irrelevant123!", "new_password": "MyOwnNewPassword1!",
    })
    token = response.json()["access_token"]

    heartbeat_resp = client.post("/auth/heartbeat", headers={"Authorization": f"Bearer {token}"})
    assert heartbeat_resp.status_code == 200


def test_login_with_valid_credentials_but_must_change_password_returns_no_token(client, db):
    """The real, actual enforcement point: valid credentials alone aren't enough to get a usable token if the account's password was admin-set -- no token means no way to make an authenticated request until change-password is actually used."""
    user = make_plain_user(db)
    user.must_change_password = True
    db.commit()

    response = client.post("/auth/login", json={"email": user.email, "password": "Irrelevant123!"})
    assert response.status_code == 200
    body = response.json()
    assert body == {"must_change_password": True}
    assert "access_token" not in body
