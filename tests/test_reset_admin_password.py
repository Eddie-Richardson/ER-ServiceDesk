# ER-ServiceDesk/tests/test_reset_admin_password.py
"""
Covers app.db.reset_admin_password.reset_admin_password() -- the
emergency, database-direct admin password recovery script. Mocks
input()/getpass.getpass() (the script's own real interactive prompts)
and SessionLocal (so it operates on the test database, not a real one)
to exercise every distinct real branch: success, wrong account type,
unknown email, mismatched confirmation, and weak password rejection.
"""

from unittest.mock import patch

from app.core.security import verify_password
from app.db import reset_admin_password as reset_admin_password_module
from tests.conftest import TestSessionLocal


def _make_superuser(db, email="admin@myrealshop.com"):
    from app.models.user import User
    user = User(
        email=email, first_name="Eddie", last_name="Richardson",
        hashed_password="original-hash", is_active=True, is_superuser=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_non_superuser(db, email="agent@myrealshop.com"):
    from app.models.user import User
    user = User(
        email=email, first_name="Regular", last_name="Agent",
        hashed_password="original-hash", is_active=True, is_superuser=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def test_resets_a_real_superusers_password(db, monkeypatch):
    """The core, real success path -- a superuser's password genuinely changes, and the new value verifies correctly."""
    user = _make_superuser(db)
    monkeypatch.setattr(reset_admin_password_module, "SessionLocal", TestSessionLocal)

    with patch("builtins.input", return_value=user.email), \
         patch("getpass.getpass", side_effect=["RealPassword1!", "RealPassword1!"]):
        reset_admin_password_module.reset_admin_password()

    db.refresh(user)
    assert verify_password("RealPassword1!", user.hashed_password)


def test_rejects_a_non_superuser_account_without_changing_it(db, monkeypatch):
    """This script is deliberately restricted to superuser recovery only -- a non-superuser's password must stay genuinely untouched."""
    user = _make_non_superuser(db)
    monkeypatch.setattr(reset_admin_password_module, "SessionLocal", TestSessionLocal)

    with patch("builtins.input", return_value=user.email), \
         patch("getpass.getpass", side_effect=["RealPassword1!", "RealPassword1!"]):
        reset_admin_password_module.reset_admin_password()

    db.refresh(user)
    assert user.hashed_password == "original-hash"


def test_unknown_email_changes_nothing(db, monkeypatch):
    """An email with no matching account at all is a clean no-op, not an error."""
    monkeypatch.setattr(reset_admin_password_module, "SessionLocal", TestSessionLocal)

    with patch("builtins.input", return_value="nobody@example.com"), \
         patch("getpass.getpass", side_effect=["RealPassword1!", "RealPassword1!"]):
        reset_admin_password_module.reset_admin_password()  # must not raise


def test_mismatched_confirmation_changes_nothing(db, monkeypatch):
    """Typing the new password differently from its confirmation leaves the account genuinely untouched."""
    user = _make_superuser(db)
    monkeypatch.setattr(reset_admin_password_module, "SessionLocal", TestSessionLocal)

    with patch("builtins.input", return_value=user.email), \
         patch("getpass.getpass", side_effect=["RealPassword1!", "SomethingElse2!"]):
        reset_admin_password_module.reset_admin_password()

    db.refresh(user)
    assert user.hashed_password == "original-hash"


def test_weak_password_is_rejected_without_changing_anything(db, monkeypatch):
    """A password failing hash_password()'s own real strength check leaves the account genuinely untouched, not partially updated."""
    user = _make_superuser(db)
    monkeypatch.setattr(reset_admin_password_module, "SessionLocal", TestSessionLocal)

    with patch("builtins.input", return_value=user.email), \
         patch("getpass.getpass", side_effect=["weak", "weak"]):
        reset_admin_password_module.reset_admin_password()

    db.refresh(user)
    assert user.hashed_password == "original-hash"
