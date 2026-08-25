# ER-ServiceDesk/desktop/app_paths.py

"""
Resolves the two paths the app needs to find itself by, correctly in
both dev mode and as a packaged PyInstaller .exe -- these behave
differently enough that getting this wrong is one of the most common
ways a packaged Python app silently breaks.

In dev mode (`python -m desktop.main`), everything -- desktop source,
backend source, docker-compose.yml -- lives together in one checked-out
repo, so paths can be found relative to this file.

Once packaged, PyInstaller extracts the app into a temporary directory
that isn't guaranteed to exist between runs (`sys._MEIPASS`), so
anything that needs to persist across restarts -- docker-compose.yml,
the backend source Docker builds from, and the generated .env -- can't
live there. Those instead live in a fixed, permanent location the Inno
installer places them in: Program Files\\ER-ServiceDesk\\. The icon,
by contrast, is read-only and never changes after packaging, so it's
fine for it to live inside PyInstaller's bundle.

Program Files, not %LOCALAPPDATA%, deliberately -- this project moved
away from a per-user install location once the installer started
requiring admin rights (PrivilegesRequired=admin). The real-world
scenario driving this: software in a business setting is typically
installed once by whoever has admin rights, but may be used by a
different employee logging into that same PC later. A per-user
location tied to whichever specific account happened to run the
installer wouldn't be found by anyone else logging in; Program Files
is visible to every account on the machine regardless of who set it up.

`sys.frozen` is the standard flag PyInstaller sets on `sys` at runtime
to signal "this is a packaged build" -- checking it is the normal,
documented way to branch this kind of path logic.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

APP_DATA_DIR_NAME = "ER-ServiceDesk"
ENV_BACKUP_DIR_NAME = "ER-ServiceDesk-Backup"


def is_frozen() -> bool:
    """Returns whether this is running as a packaged PyInstaller build, rather than dev mode."""
    return getattr(sys, "frozen", False)


def get_compose_dir() -> str:
    """
    Returns the directory containing docker-compose.yml, the backend
    source, and .env.

    In dev mode, this is the project root (one level up from desktop/).
    In a packaged build, this is the fixed, permanent location the Inno
    installer placed these files in -- Program Files\\ER-ServiceDesk\\ --
    since PyInstaller's own extraction directory isn't a safe place for
    anything that needs to persist across app restarts.
    """
    if is_frozen():
        program_files = os.environ.get("ProgramFiles")
        if not program_files:
            # Extremely unlikely on real Windows, but fail loudly rather
            # than silently pointing at a wrong/empty path if it ever happens.
            raise RuntimeError("ProgramFiles environment variable not set.")
        return str(Path(program_files) / APP_DATA_DIR_NAME)

    return str(Path(__file__).resolve().parent.parent)


def get_env_backup_dir() -> str:
    """
    Returns the directory holding a backup copy of .env -- the one file
    among everything the Inno installer installs that's genuinely
    irreplaceable, since it holds the unique password already baked
    into the live database and the unique SECRET_KEY signing active
    sessions. Everything else the installer places (docker-compose.yml,
    the backend source, the exe itself)
    is identical every install and trivially restored by a repair/
    reinstall, so only .env needs this safety net.

    Deliberately a sibling folder to the main install, not a subfolder
    inside it -- if the main ER-ServiceDesk folder itself gets deleted
    (by accident, a bad cleanup tool, antivirus overreach), a backup
    living inside that same folder would vanish right along with it.

    Living under Program Files means restoring this backup (see
    env_recovery.py) requires admin rights, same as installing it did
    in the first place -- consistent with how this project is actually
    used: Local is realistically a single shop owner who's already an
    admin on their own PC, and Server is headless, only ever touched
    directly by IT/admin staff. Client never has a .env at all, so
    this restore path never applies to the one case with a genuinely
    non-admin regular employee.
    """
    if is_frozen():
        program_files = os.environ.get("ProgramFiles")
        if not program_files:
            raise RuntimeError("ProgramFiles environment variable not set.")
        return str(Path(program_files) / ENV_BACKUP_DIR_NAME)

    return str(Path(__file__).resolve().parent.parent.parent / ENV_BACKUP_DIR_NAME)


def get_icon_path() -> str:
    """
    Returns the path to the app icon.

    In dev mode, this is desktop/assets/icon.ico relative to this file.
    In a packaged build, PyInstaller bundles data files alongside the
    .exe (or, for a onefile build, extracts them to sys._MEIPASS at
    runtime) -- either way, sys.executable's own directory / _MEIPASS
    is the correct place to look, not this file's location, which
    would point somewhere inside PyInstaller's internal bundle
    structure rather than the actual bundled asset.
    """
    if is_frozen():
        base_dir = getattr(sys, "_MEIPASS", None) or str(Path(sys.executable).resolve().parent)
        return str(Path(base_dir) / "assets" / "icon.ico")

    return str(Path(__file__).resolve().parent / "assets" / "icon.ico")


def debug_log(message: str):
    """
    Appends a timestamped line to a small diagnostic log file in
    %TEMP%, for tracing down issues that are hard to reproduce without
    real customer data or hardware. Kept permanently, not a temporary
    debugging aid -- same reasoning as main.py's own crash log: there's
    no way to ask a remote customer to reproduce an issue with logging
    added after the fact, so it's better to already be there.

    Never raises -- a failure to write a debug log line should never
    be the thing that crashes the app.
    """
    try:
        log_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-debug-log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n")
    except Exception:
        pass
