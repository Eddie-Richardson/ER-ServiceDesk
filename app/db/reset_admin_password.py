# ER-ServiceDesk/app/db/reset_admin_password.py

"""
Emergency admin password recovery script.

Run this directly when locked out of the app with nobody else able to
reset your password for you -- it bypasses the app entirely and resets
a superuser account's password straight in the database.

Usage (from the project root, in a terminal):
    docker-compose exec -it api python -m app.db.reset_admin_password

The -it flag matters: without it, this script can't prompt you for
input inside the container. Follow the prompts for the account's email
and a new password.

Deliberately restricted to superuser accounts only -- this is a
last-resort admin recovery tool, not a general password-reset backdoor
for arbitrary accounts. Resetting a non-admin's password is what the
Reset Password button in the Users & Roles window is for, once you're
back in.
"""

import getpass

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def reset_admin_password():
    db = SessionLocal()

    email = input("Email of the superuser account to reset: ").strip()
    user = db.query(User).filter_by(email=email).first()

    if not user:
        print(f"No account found with email '{email}'.")
        db.close()
        return

    if not user.is_superuser:
        print(
            f"'{email}' is not a superuser account. This script only resets "
            f"superuser passwords -- use the Reset Password button in the "
            f"Users & Roles window for other accounts."
        )
        db.close()
        return

    new_password = getpass.getpass("New password (won't be shown as you type): ")
    confirm_password = getpass.getpass("Confirm new password: ")

    if new_password != confirm_password:
        print("Passwords didn't match. Nothing was changed.")
        db.close()
        return

    if not new_password:
        print("Password can't be empty. Nothing was changed.")
        db.close()
        return

    user.hashed_password = hash_password(new_password)
    db.commit()
    db.close()

    print(f"Password reset successfully for {email}.")


if __name__ == "__main__":
    reset_admin_password()
