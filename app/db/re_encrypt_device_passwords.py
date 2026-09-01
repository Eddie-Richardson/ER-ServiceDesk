# ER-ServiceDesk/app/db/re_encrypt_device_passwords.py

"""
Standalone entrypoint, run inside the API container by
RestoreDatabaseLocal.exe after a database restore -- decrypts every
device user account password with the OLD machine's encryption key
(the one that originally encrypted them, read from a .key file the
backup process wrote alongside the .dump) and re-encrypts with THIS
machine's own current DEVICE_ACCOUNT_ENCRYPTION_KEY.

Without this, restoring a database backed up on a different machine
(new hardware, a fresh PC) would leave every stored device account
password permanently undecryptable -- the restored rows would still be
encrypted with the old machine's key, not this one's.

Deliberately reuses the real, existing encrypt_password()/
decrypt_password() functions (see app/core/encryption.py) rather than
a separate copy of the same Fernet/PBKDF2 logic -- this runs inside the
API container specifically so it has access to those functions
directly, avoiding any risk of a second, subtly different
reimplementation drifting from the original over time.

Usage:
    docker-compose exec api python -m app.db.re_encrypt_device_passwords <old_key>
"""

import sys

from app.core.config import settings
from app.core.encryption import encrypt_password, decrypt_password
from app.db.session import SessionLocal
from app.models.device_user_account import DeviceUserAccount


def run(old_key: str):
    """
    Args:
        old_key: The DEVICE_ACCOUNT_ENCRYPTION_KEY that originally
            encrypted the restored database's device_user_accounts
            rows -- read from the backup's own .key file by the
            caller, not looked up here.

    Exits with status 0 on success, 1 on failure -- the exit code is
    what RestoreDatabaseLocal.exe actually checks, not the printed
    output.
    """
    new_key = settings.DEVICE_ACCOUNT_ENCRYPTION_KEY
    if not new_key:
        print("This machine's own DEVICE_ACCOUNT_ENCRYPTION_KEY is not set -- cannot re-encrypt.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        accounts = db.query(DeviceUserAccount).filter(DeviceUserAccount.encrypted_password.isnot(None)).all()

        if not accounts:
            print("No device user account passwords found -- nothing to re-encrypt.")
            return

        # Decrypt every row with the OLD key first, all at once, before
        # re-encrypting any of them with the NEW key -- so a decrypt
        # failure partway through (e.g. old_key doesn't actually match
        # what these rows were encrypted with) is caught before this
        # has touched the database at all, rather than leaving some
        # rows re-encrypted and others not.
        settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = old_key
        try:
            decrypted_by_id = {account.id: decrypt_password(account.encrypted_password) for account in accounts}
        except Exception as e:
            print(f"Failed to decrypt with the provided old key -- it may not match what these passwords were actually encrypted with: {e}", file=sys.stderr)
            sys.exit(1)
        finally:
            settings.DEVICE_ACCOUNT_ENCRYPTION_KEY = new_key

        for account in accounts:
            account.encrypted_password = encrypt_password(decrypted_by_id[account.id])

        db.commit()
        print(f"Re-encrypted {len(accounts)} device user account password(s) with this machine's own key.")
    except Exception as e:
        db.rollback()
        print(f"Re-encryption failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.db.re_encrypt_device_passwords <old_key>", file=sys.stderr)
        sys.exit(1)
    run(sys.argv[1])
