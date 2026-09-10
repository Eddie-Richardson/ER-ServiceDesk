# ER-ServiceDesk/tests/test_user_security.py
"""
The original codebase leaked `hashed_password` in every user API response,
and required clients to submit an already-hashed password on create. Both
were fixed; these tests exist so neither regresses silently.
"""


def test_create_user_response_excludes_hashed_password(client, superuser_headers, monkeypatch):
    """Creating a user never echoes back the hash, even though it accepts a plaintext password."""
    monkeypatch.setattr("app.services.user_service.send_email", lambda db, **kwargs: None)
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


def test_list_users_excludes_hashed_password(client, superuser_headers, db, monkeypatch):
    """Listing users never includes the hash for any account, including seeded ones."""
    monkeypatch.setattr("app.services.user_service.send_email", lambda db, **kwargs: None)
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


def test_created_user_password_is_actually_hashed_in_db(client, superuser_headers, db, monkeypatch):
    """The stored hashed_password is never the plaintext password itself."""
    from app.models.user import User
    monkeypatch.setattr("app.services.user_service.send_email", lambda db, **kwargs: None)

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


def test_hash_password_rejects_a_password_over_the_byte_limit():
    """72 bytes is bcrypt's own real limit -- a genuinely too-long password is rejected with a specific, clear message, not silently truncated."""
    import pytest
    from app.core.security import hash_password
    too_long = "Aa1!" + "x" * 70  # over 72 bytes, satisfies every other rule
    with pytest.raises(ValueError, match="72 bytes"):
        hash_password(too_long)


def test_hash_password_rejects_a_password_missing_an_uppercase_letter():
    import pytest
    from app.core.security import hash_password
    with pytest.raises(ValueError, match="uppercase"):
        hash_password("alllowercase1!")


def test_hash_password_rejects_a_password_missing_a_lowercase_letter():
    import pytest
    from app.core.security import hash_password
    with pytest.raises(ValueError, match="lowercase"):
        hash_password("ALLUPPERCASE1!")


def test_hash_password_rejects_a_password_missing_a_digit():
    import pytest
    from app.core.security import hash_password
    with pytest.raises(ValueError, match="number"):
        hash_password("NoDigitsHere!")


def test_hash_password_rejects_a_password_missing_a_special_character():
    import pytest
    from app.core.security import hash_password
    with pytest.raises(ValueError, match="special character"):
        hash_password("NoSpecial1Here")


def test_hash_password_accepts_a_password_meeting_every_real_rule():
    from app.core.security import hash_password, verify_password
    result = hash_password("ValidPassword1!")
    assert verify_password("ValidPassword1!", result)
