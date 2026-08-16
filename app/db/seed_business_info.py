# ER-ServiceDesk/app/db/seed_business_info.py

"""
Standalone entrypoint for seeding business info (name, phone, email
account, SMTP/IMAP) directly into the database at install time --
these are real SystemSetting rows (see
app/services/business_info_service.py), never written to .env at all,
not even for a moment.

Reads every value from environment variables rather than command-line
arguments, since one of them (the email password) is a real secret --
CLI arguments are visible to anything that can list running processes
on the machine (e.g. `ps aux`), environment variables passed via
`docker-compose exec -e` are not exposed the same way.

Idempotent, same reasoning as run_seed.py -- upsert(), not insert(),
so a wizard retry after a different step failed is always safe.

Usage:
    docker-compose exec -T \\
      -e BUSINESS_NAME=... -e BUSINESS_PHONE=... \\
      -e EMAIL_ADDRESS=... -e EMAIL_PASSWORD=... \\
      -e SMTP_HOST=... -e SMTP_PORT=... -e IMAP_HOST=... -e IMAP_PORT=... \\
      api python -m app.db.seed_business_info
"""

import os
import sys

from app.db.session import SessionLocal
from app.services.business_info_service import business_info_service
from app.schemas.business_info import BusinessInfoUpdate


def run():
    """
    Reads business info values from the environment and saves them via
    business_info_service.update() -- the exact same path the desktop
    Settings -> Business Info screen uses, so the email password ends
    up encrypted the same way either way.

    Exits with status 0 on success, 1 on failure -- the exit code is
    what the installer's subprocess call actually checks.
    """
    db = SessionLocal()
    try:
        obj_in = BusinessInfoUpdate(
            business_name=os.environ.get("BUSINESS_NAME", ""),
            business_phone=os.environ.get("BUSINESS_PHONE", ""),
            email_address=os.environ.get("EMAIL_ADDRESS", ""),
            email_password=os.environ.get("EMAIL_PASSWORD") or None,
            smtp_host=os.environ.get("SMTP_HOST", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            imap_host=os.environ.get("IMAP_HOST", "imap.gmail.com"),
            imap_port=int(os.environ.get("IMAP_PORT", "993")),
        )
        business_info_service.update(db, obj_in)
    except Exception as e:
        print(f"Business info seeding failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
