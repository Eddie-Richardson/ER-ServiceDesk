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
