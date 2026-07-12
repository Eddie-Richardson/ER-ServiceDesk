# ER-ServiceDesk/desktop/settings_manager.py

"""
Per-machine app settings, backed by QSettings.

QSettings stores data in the OS-native location automatically -- the
Windows registry on Windows, a plist on macOS, an ini file on Linux.
This gives us "remember the theme choice for this machine" without
writing any platform-specific code ourselves.
"""

from PySide6.QtCore import QSettings

ORG_NAME = "ERServiceRepairNC"
APP_NAME = "ER-ServiceDesk"

THEME_KEY = "appearance/theme"
DEFAULT_THEME = "light"


def get_saved_theme() -> str:
    """
    Returns the saved theme preference for this machine ("light" or "dark").
    Falls back to the default if nothing has been saved yet, or if the
    stored value is somehow invalid.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    value = settings.value(THEME_KEY, DEFAULT_THEME)
    return value if value in ("light", "dark") else DEFAULT_THEME


def save_theme(theme_name: str):
    """
    Persists the given theme preference for this machine.

    Args:
        theme_name: Either "light" or "dark".
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(THEME_KEY, theme_name)
