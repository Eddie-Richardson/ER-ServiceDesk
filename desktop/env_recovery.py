# ER-ServiceDesk/desktop/env_recovery.py

"""
Safety net for the one file this app cannot function without: .env.

The installer writes .env to the main install location during setup, and copies
an identical backup to a separate sibling folder (see
app_paths.get_env_backup_dir()) at the same time. If .env ever goes
missing from the main location afterward -- accidental deletion, a bad
cleanup tool, antivirus overreach -- this module is what main.py calls
before doing anything else, to quietly restore it from that backup
rather than crash or require a full reinstall.

Deliberately narrow in scope: this only recovers from "the file got
deleted from one of two known locations." If both copies are gone,
that's a real problem this module can't solve on its own -- the
password baked into the live database is already gone with it, and
recovering that means restoring from a real database backup (a
separate, larger topic), not just regenerating a new .env.
"""

import shutil
from pathlib import Path


def ensure_env_available(compose_dir: str, backup_dir: str) -> bool:
    """
    Confirms .env exists at the main install location, restoring it
    from the backup location first if it's missing there but present
    in the backup.

    Args:
        compose_dir: The main install directory .env should live in
            (see app_paths.get_compose_dir()).
        backup_dir: The sibling backup directory holding a copy of
            .env (see app_paths.get_env_backup_dir()).

    Returns:
        True if .env exists at compose_dir by the time this returns
        (whether it was already there or just restored). False only if
        it's missing from both locations -- meaning it genuinely
        cannot be recovered automatically.
    """
    main_env_path = Path(compose_dir) / ".env"
    if main_env_path.exists():
        return True

    backup_env_path = Path(backup_dir) / ".env"
    if not backup_env_path.exists():
        return False

    try:
        Path(compose_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_env_path, main_env_path)
    except OSError:
        # Restoring failed for some environmental reason (permissions,
        # disk full, etc.) -- report as unavailable rather than assume
        # the copy silently worked.
        return False

    return main_env_path.exists()
