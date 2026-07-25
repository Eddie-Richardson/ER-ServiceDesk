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
live there. Those instead live in a fixed, permanent location the WiX
installer places them in: %LOCALAPPDATA%\\ER-ServiceDesk\\. The icon,
by contrast, is read-only and never changes after packaging, so it's
fine for it to live inside PyInstaller's bundle.

`sys.frozen` is the standard flag PyInstaller sets on `sys` at runtime
to signal "this is a packaged build" -- checking it is the normal,
documented way to branch this kind of path logic.
"""

import os
import sys
from pathlib import Path

APP_DATA_DIR_NAME = "ER-ServiceDesk"


def is_frozen() -> bool:
    """Returns whether this is running as a packaged PyInstaller build, rather than dev mode."""
    return getattr(sys, "frozen", False)


def get_compose_dir() -> str:
    """
    Returns the directory containing docker-compose.yml, the backend
    source, and .env.

    In dev mode, this is the project root (one level up from desktop/).
    In a packaged build, this is the fixed, permanent location the WiX
    installer placed these files in -- %LOCALAPPDATA%\\ER-ServiceDesk\\ --
    since PyInstaller's own extraction directory isn't a safe place for
    anything that needs to persist across app restarts.
    """
    if is_frozen():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            # Extremely unlikely on real Windows, but fail loudly rather
            # than silently pointing at a wrong/empty path if it ever happens.
            raise RuntimeError("LOCALAPPDATA environment variable not set.")
        return str(Path(local_app_data) / APP_DATA_DIR_NAME)

    return str(Path(__file__).resolve().parent.parent)


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
