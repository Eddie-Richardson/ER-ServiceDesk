# ER-ServiceDesk/tests/test_user_service.py
"""
Covers UserService.create(), reset_password(), update(), and delete()
-- the ordinary user-management methods, distinct from
create_first_run_admin() (see test_first_run_admin.py). Focuses on
the real, non-obvious properties: an account whose welcome/reset email
fails to send is deliberately never created/changed at all, duplicate
email checks, and that an audit log entry only fires when something
genuinely changed.
"""

import pytest
from fastapi import HTTPException

from app.services.user_service import user_service
from app.schemas.user import UserCreate, UserUpdate
from app.models.user import User
from app.crud.audit_log import crud_audit_log
from tests.factories import make_plain_user


def _user_create(email="newuser@example.com", **overrides):
    defaults = dict(email=email, first_name="New", last_name="User")
    defaults.update(overrides)
    return UserCreate(**defaults)


def _actor(db):
    """AuditLog.user_id has a real foreign key constraint -- every call needs a genuinely persisted user to attribute the action to, not an arbitrary integer."""
    return make_plain_user(db, email="actor@example.com").id


def test_create_rejects_a_duplicate_email(db):
    existing = make_plain_user(db)
    actor_id = _actor(db)
    with pytest.raises(HTTPException) as exc_info:
        user_service.create(db, _user_create(email=existing.email), current_user_id=actor_id)
    assert exc_info.value.status_code == 400


def test_create_never_creates_an_account_if_the_welcome_email_fails(db, monkeypatch):
    """The real, deliberate ordering: an account whose password email nobody actually received is worse than no account at all."""
    actor_id = _actor(db)
    monkeypatch.setattr(
        "app.services.user_service.send_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )

    with pytest.raises(HTTPException) as exc_info:
        user_service.create(db, _user_create(), current_user_id=actor_id)
    assert exc_info.value.status_code == 500
    assert db.query(User).filter_by(email="newuser@example.com").first() is None


def test_create_succeeds_with_a_hashed_temp_password_requiring_change(db, monkeypatch):
    actor_id = _actor(db)
    monkeypatch.setattr("app.services.user_service.send_email", lambda **kwargs: None)

    created = user_service.create(db, _user_create(), current_user_id=actor_id)

    assert created.must_change_password is True
    assert created.hashed_password != ""
    # A real bcrypt hash, not the plaintext temp password stored directly.
    assert created.hashed_password.startswith("$2b$")


def test_reset_password_returns_404_for_a_nonexistent_user(db):
    actor_id = _actor(db)
    with pytest.raises(HTTPException) as exc_info:
        user_service.reset_password(db, id=999999, current_user_id=actor_id)
    assert exc_info.value.status_code == 404


def test_reset_password_leaves_the_password_unchanged_if_the_email_fails(db, monkeypatch):
    user = make_plain_user(db)
    actor_id = _actor(db)
    original_hash = user.hashed_password
    monkeypatch.setattr(
        "app.services.user_service.send_email",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("SMTP is down")),
    )

    with pytest.raises(HTTPException) as exc_info:
        user_service.reset_password(db, user.id, current_user_id=actor_id)
    assert exc_info.value.status_code == 500

    db.refresh(user)
    assert user.hashed_password == original_hash


def test_reset_password_genuinely_changes_the_hash_and_requires_a_new_one(db, monkeypatch):
    user = make_plain_user(db)
    actor_id = _actor(db)
    original_hash = user.hashed_password
    monkeypatch.setattr("app.services.user_service.send_email", lambda **kwargs: None)

    updated = user_service.reset_password(db, user.id, current_user_id=actor_id)

    assert updated.hashed_password != original_hash
    assert updated.must_change_password is True


def test_update_rejects_changing_email_to_one_already_used_by_a_different_account(db):
    user_a = make_plain_user(db, email="usera@example.com")
    user_b = make_plain_user(db, email="userb@example.com")
    actor_id = _actor(db)

    with pytest.raises(HTTPException) as exc_info:
        user_service.update(db, user_a.id, UserUpdate(email="userb@example.com"), current_user_id=actor_id)
    assert exc_info.value.status_code == 400

    db.refresh(user_a)
    assert user_a.email == "usera@example.com"


def test_update_allows_keeping_your_own_unchanged_email(db):
    """Submitting the same email you already have isn't a genuine conflict with yourself."""
    user = make_plain_user(db, email="same@example.com")
    actor_id = _actor(db)
    updated = user_service.update(db, user.id, UserUpdate(email="same@example.com", first_name="Updated"), current_user_id=actor_id)
    assert updated.first_name == "Updated"


def test_update_only_logs_an_audit_entry_when_something_genuinely_changed(db):
    user = make_plain_user(db)  # first_name defaults to "Plain"
    actor_id = _actor(db)

    user_service.update(db, user.id, UserUpdate(first_name="Plain"), current_user_id=actor_id)
    entries_after_noop = crud_audit_log.get_multi(db, limit=500)
    noop_actions = [e for e in entries_after_noop if e.entity_type == "user" and e.entity_id == user.id and e.action == "user_updated"]
    assert len(noop_actions) == 0

    user_service.update(db, user.id, UserUpdate(first_name="Genuinely Changed"), current_user_id=actor_id)
    entries_after_real_change = crud_audit_log.get_multi(db, limit=500)
    real_actions = [e for e in entries_after_real_change if e.entity_type == "user" and e.entity_id == user.id and e.action == "user_updated"]
    assert len(real_actions) == 1


def test_delete_logs_the_deleted_users_email_even_though_the_account_is_gone_afterward(db):
    user = make_plain_user(db, email="doomed@example.com")
    actor_id = _actor(db)
    user_id = user.id

    user_service.delete(db, user_id, current_user_id=actor_id)

    assert db.query(User).filter_by(id=user_id).first() is None

    entries = crud_audit_log.get_multi(db, limit=500)
    delete_entry = next(e for e in entries if e.entity_type == "user" and e.entity_id == user_id and e.action == "user_deleted")
    assert "doomed@example.com" in delete_entry.details
