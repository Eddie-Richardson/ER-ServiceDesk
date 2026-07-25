# ER-ServiceDesk/app/db/run_seed.py

"""
Standalone entrypoint for running seed_data().

Exists as a clean, dedicated script rather than the inline
`python -c "..."` one-liner used throughout this project's manual setup
steps -- that works fine for a human to copy-paste once, but is fragile
to invoke from another script (shell-escaping, no clear success/failure
signal), which matters now that the Setup Wizard needs to run this
programmatically rather than a person typing it by hand.

seed_data() is idempotent -- every insert checks whether its row
already exists first -- so running this multiple times (e.g. a wizard
retry after a different step failed) is always safe.

Usage:
    docker-compose exec api python -m app.db.run_seed
"""

import os
import sys

from app.db.session import SessionLocal
from app.db.seed import seed_data


def run():
    """
    Runs seed_data() against a real database session, passing through
    BUSINESS_NAME from the environment if the Setup Wizard set one in
    .env.

    Exits with status 0 on success, 1 on failure -- the exit code is
    what a calling script (like the Setup Wizard's subprocess call)
    actually checks, not the printed output.
    """
    db = SessionLocal()
    try:
        seed_data(db, business_name=os.environ.get("BUSINESS_NAME"))
    except Exception as e:
        print(f"Seeding failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
