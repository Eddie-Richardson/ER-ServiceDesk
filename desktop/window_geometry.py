# ER-ServiceDesk/desktop/window_geometry.py

"""
Per-machine window size/position memory, backed by QSettings.

Mirrors settings_manager.py's theme-persistence pattern (same
ORG_NAME/APP_NAME, so it's stored right alongside the theme setting).
Each window/dialog type remembers its own size and position
independently, keyed by a short string the caller provides -- so the
Tickets window and the Asset dialog each keep their own remembered
geometry, not one shared size for everything.

Usage, at the end of a window/dialog's __init__ (after its layout is
built, so restoring a size actually has something to size against):

    restore_geometry(self, "TicketsWindow")

And in its closeEvent (or wherever the window is about to close):

    save_geometry(self, "TicketsWindow")
"""

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget

ORG_NAME = "ERServiceRepairNC"
APP_NAME = "ER-ServiceDesk"


def _key(window_key: str) -> str:
    """
    Args:
        window_key: The caller-provided identifier, e.g. "TicketsWindow".

    Returns:
        The full QSettings key this geometry is stored under.
    """
    return f"geometry/{window_key}"


def save_geometry(window: QWidget, window_key: str):
    """
    Persists a window's current size and position for this machine.

    Args:
        window: The window or dialog whose geometry to save.
        window_key: A short identifier unique to this window/dialog
            type, e.g. "TicketsWindow" or "AssetFormDialog". Every
            instance of the same type shares one remembered geometry.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(_key(window_key), window.saveGeometry())


def restore_geometry(window: QWidget, window_key: str):
    """
    Restores a previously saved size and position, if one exists. Does
    nothing if this window/dialog type has never been saved before --
    it simply keeps whatever size the window was already constructed
    with.

    Args:
        window: The window or dialog to restore geometry onto.
        window_key: The same identifier used in save_geometry().
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    saved = settings.value(_key(window_key))
    if saved is not None:
        window.restoreGeometry(saved)
