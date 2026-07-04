# ER-ServiceDesk/tests/test_user_security.py
# Regression tests guarding the password-hash-leak bug found in the initial audit.
"""
The original codebase leaked `hashed_password` in every user API response,
and required clients to submit an already-hashed password on create. Both
were fixed; these tests exist so neither regresses silently.
"""


def test_create_user_response_excludes_hashed_password(client, superuser_headers):
    """Creating a user never echoes back the hash, even though it accepts a plaintext password."""
    response = client.post(
        "/users/",
        json={
            "email": "newstaff@example.com",
            "password": "plaintext-password-123",
            "first_name": "New",
            "last_name": "Staff",
        },
        headers=superuser_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert "hashed_password" not in body
    assert "password" not in body


def test_list_users_excludes_hashed_password(client, superuser_headers, db):
    """Listing users never includes the hash for any account, including seeded ones."""
    client.post(
        "/users/",
        json={
            "email": "liststaff@example.com",
            "password": "plaintext-password-123",
            "first_name": "List",
            "last_name": "Staff",
        },
        headers=superuser_headers,
    )

    response = client.get("/users/", headers=superuser_headers)
    assert response.status_code == 200
    for user in response.json():
        assert "hashed_password" not in user


def test_created_user_password_is_actually_hashed_in_db(client, superuser_headers, db):
    """The stored hashed_password is never the plaintext password itself."""
    from app.models.user import User

    client.post(
        "/users/",
        json={
            "email": "hashcheck@example.com",
            "password": "plaintext-password-123",
            "first_name": "Hash",
            "last_name": "Check",
        },
        headers=superuser_headers,
    )

    stored = db.query(User).filter(User.email == "hashcheck@example.com").first()
    assert stored is not None
    assert stored.hashed_password != "plaintext-password-123"
    assert stored.hashed_password.startswith("$2b$")  # bcrypt hash prefix
