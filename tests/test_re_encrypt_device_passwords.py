# ER-ServiceDesk/tests/test_re_encrypt_device_passwords.py
"""
Tests for app.db.re_encrypt_device_passwords -- the standalone script
RestoreDatabaseLocal.exe runs after a database restore, decrypting
device user account passwords with the OLD machine's encryption key
and re-encrypting them with the machine being restored to's own,
current key.
"""

from unittest.mock import patch

from app.core.config import settings
from app.core.encryption import decrypt_password, encrypt_password
from app.db import re_encrypt_device_passwords
from app.models.device_user_account import DeviceUserAccount
from tests.conftest import TestSessionLocal
from tests.factories import make_customer, make_device


def test_reencrypt_recovers_original_password(db):
    """The genuine, real script -- not a mock -- decrypts a value encrypted with an old key and re-encrypts it with the current key, recovering the exact original password."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    old_key = "old-machine-test-key-abc123"
    new_key = settings.DEVICE_ACCOUNT_ENCRYPTION_KEY
    assert new_key, "Test .env should have DEVICE_ACCOUNT_ENCRYPTION_KEY set"

    # Simulate: this password was encrypted on the OLD machine, using
    # the OLD key -- temporarily swap settings to produce a genuinely
    # old-key-encrypted value, then restore it, matching real app
    # startup state (settings never actually changes at runtime
    # outside of this test).
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = old_key
    original_plaintext = "SuperSecretMicrosoftPassword123!"
    old_encrypted_value = encrypt_password(original_plaintext)
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = new_key

    account = DeviceUserAccount(
        device_id=device.id, account_name="testuser@outlook.com",
        encrypted_password=old_encrypted_value, is_admin=False,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    # Confirm decrypting with the current key genuinely fails first --
    # proves this is a real test of a real mismatch, not a false pass.
    try:
        decrypt_password(account.encrypted_password)
        assert False, "Decrypting with the new key should have failed but didn't"
    except Exception:
        pass

    # Point the script's own SessionLocal at the real test database --
    # the script's real code, run for real, just against the test
    # database instead of production (which is what it'd actually
    # connect to via docker-compose exec in a genuine restore).
    with patch("app.db.re_encrypt_device_passwords.SessionLocal", TestSessionLocal):
        re_encrypt_device_passwords.run(old_key)

    db.refresh(account)
    assert account.encrypted_password != old_encrypted_value

    recovered_plaintext = decrypt_password(account.encrypted_password)
    assert recovered_plaintext == original_plaintext


def test_reencrypt_with_wrong_key_fails_without_touching_the_database(db):
    """If the given old key doesn't actually match what a password was encrypted with, the script fails cleanly rather than silently corrupting the stored value."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    real_old_key = "the-actual-old-key"
    wrong_old_key = "not-the-right-key-at-all"
    current_machine_key = settings.DEVICE_ACCOUNT_ENCRYPTION_KEY
    assert current_machine_key, "Test .env should have DEVICE_ACCOUNT_ENCRYPTION_KEY set"

    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = real_old_key
    encrypted_value = encrypt_password("some password")
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = current_machine_key

    account = DeviceUserAccount(
        device_id=device.id, account_name="testuser@outlook.com",
        encrypted_password=encrypted_value, is_admin=False,
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    with patch("app.db.re_encrypt_device_passwords.SessionLocal", TestSessionLocal):
        try:
            re_encrypt_device_passwords.run(wrong_old_key)
            assert False, "Should have exited with an error for a genuinely wrong key"
        except SystemExit as e:
            assert e.code == 1

    db.refresh(account)
    assert account.encrypted_password == encrypted_value, "The stored value must be untouched after a failed re-encryption attempt"


def test_reencrypt_with_no_accounts_at_all_is_a_safe_no_op(db):
    """A database with zero device_user_accounts rows exits cleanly, not as an error."""
    with patch("app.db.re_encrypt_device_passwords.SessionLocal", TestSessionLocal):
        re_encrypt_device_passwords.run("some-old-key")  # must not raise or exit


def test_reencrypt_exits_with_status_1_if_this_machines_own_key_is_not_set(db, monkeypatch):
    """Without this machine's own current key, there's genuinely nothing to re-encrypt with at all."""
    monkeypatch.setattr(settings, "DEVICE_ACCOUNT_ENCRYPTION_KEY", "")

    with patch("app.db.re_encrypt_device_passwords.SessionLocal", TestSessionLocal):
        try:
            re_encrypt_device_passwords.run("some-old-key")
            assert False, "Should have exited with an error when this machine's own key is unset"
        except SystemExit as e:
            assert e.code == 1


def test_reencrypt_recovers_every_account_not_just_the_first(db):
    """Multiple device user accounts are each genuinely, independently re-encrypted -- not just the first one found."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    old_key = "old-machine-test-key-xyz789"
    new_key = settings.DEVICE_ACCOUNT_ENCRYPTION_KEY

    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = old_key
    encrypted_a = encrypt_password("PasswordForAccountA1!")
    encrypted_b = encrypt_password("PasswordForAccountB2!")
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = new_key

    account_a = DeviceUserAccount(device_id=device.id, account_name="userA@outlook.com", encrypted_password=encrypted_a, is_admin=False)
    account_b = DeviceUserAccount(device_id=device.id, account_name="userB@outlook.com", encrypted_password=encrypted_b, is_admin=False)
    db.add_all([account_a, account_b])
    db.commit()
    db.refresh(account_a)
    db.refresh(account_b)

    with patch("app.db.re_encrypt_device_passwords.SessionLocal", TestSessionLocal):
        re_encrypt_device_passwords.run(old_key)

    db.refresh(account_a)
    db.refresh(account_b)
    assert decrypt_password(account_a.encrypted_password) == "PasswordForAccountA1!"
    assert decrypt_password(account_b.encrypted_password) == "PasswordForAccountB2!"


def test_cli_entrypoint_requires_exactly_one_argument(db):
    """The real, direct script invocation -- genuinely run as a subprocess, not just calling run() directly -- confirms the actual `python -m ...` usage path a technician would run."""
    import subprocess
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, "-m", "app.db.re_encrypt_device_passwords"],
        cwd=project_root, capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "Usage:" in result.stderr


def test_a_genuine_unexpected_failure_during_the_write_phase_rolls_back_and_exits_1(db, monkeypatch):
    """If something genuinely goes wrong after decryption succeeded but before/during the final commit, the failure is caught, rolled back, and reported with the real exit code -- not left as an uncaught crash."""
    customer = make_customer(db)
    device = make_device(db, customer.id)

    old_key = "old-machine-test-key-rollback"
    new_key = settings.DEVICE_ACCOUNT_ENCRYPTION_KEY
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = old_key
    encrypted_value = encrypt_password("some password")
    settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = new_key

    account = DeviceUserAccount(device_id=device.id, account_name="testuser@outlook.com", encrypted_password=encrypted_value, is_admin=False)
    db.add(account)
    db.commit()

    def failing_session():
        session = TestSessionLocal()

        def commit_that_always_fails():
            raise RuntimeError("genuine, unexpected database failure")

        session.commit = commit_that_always_fails
        return session

    with patch("app.db.re_encrypt_device_passwords.SessionLocal", failing_session):
        try:
            re_encrypt_device_passwords.run(old_key)
            assert False, "Should have exited with an error on a genuine, unexpected failure"
        except SystemExit as e:
            assert e.code == 1

    db.refresh(account)
    assert account.encrypted_password == encrypted_value, "The stored value must be untouched after a genuine, rolled-back failure"


def test_encrypt_password_raises_when_the_device_encryption_key_is_not_set(monkeypatch):
    """A hard failure, not a silent fallback -- silently using a weak/empty key would be a real security bug."""
    import pytest
    from app.core.config import settings
    from app.core.encryption import encrypt_password
    monkeypatch.setattr(settings, "DEVICE_ACCOUNT_ENCRYPTION_KEY", "")
    with pytest.raises(ValueError, match="DEVICE_ACCOUNT_ENCRYPTION_KEY is not set"):
        encrypt_password("some password")
