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

INSTALL_MODE_KEY = "deployment/install_mode"
DEFAULT_INSTALL_MODE = "local"
VALID_INSTALL_MODES = ("local", "server", "client")

BACKEND_URL_KEY = "deployment/backend_url"
DEFAULT_BACKEND_URL = "http://localhost:8000"


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


def get_install_mode() -> str:
    """
    Returns this machine's install mode: "local" (everything on this
    PC), "server" (this PC hosts the backend for others), or "client"
    (this PC only runs the desktop app, connecting to a remote server).
    Falls back to "local" if nothing has been saved yet, or if the
    stored value is somehow invalid -- "local" is the safe default,
    since it's the only mode that requires nothing else to already
    exist on the network.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    value = settings.value(INSTALL_MODE_KEY, DEFAULT_INSTALL_MODE)
    return value if value in VALID_INSTALL_MODES else DEFAULT_INSTALL_MODE


def save_install_mode(mode: str):
    """
    Persists this machine's install mode.

    Args:
        mode: One of "local", "server", "client".

    Raises:
        ValueError: If mode isn't one of the valid values -- this is a
            deployment-shape setting, not free-form text, so an invalid
            value here would silently misconfigure how the app connects
            to its backend.
    """
    if mode not in VALID_INSTALL_MODES:
        raise ValueError(f"Invalid install mode: {mode!r}. Must be one of {VALID_INSTALL_MODES}.")
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(INSTALL_MODE_KEY, mode)


def get_backend_url() -> str:
    """
    Returns the backend URL this machine should talk to. Defaults to
    localhost for Local/Server mode (where the backend runs on this
    same machine); Client mode installs save a real network address
    here instead, pointed at whichever machine is running Server mode.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    return settings.value(BACKEND_URL_KEY, DEFAULT_BACKEND_URL)


def save_backend_url(url: str):
    """
    Persists the backend URL this machine should talk to.

    Args:
        url: A full base URL, e.g. "http://localhost:8000" or
            "http://192.168.1.50:8000". No trailing slash.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(BACKEND_URL_KEY, url)


BUSINESS_NAME_KEY = "deployment/business_name"


def get_business_name() -> str:
    """
    Returns this shop's display name, as set during the Setup Wizard.
    Empty string if never set (e.g. still on a pre-wizard install).

    Cached locally rather than fetched from the backend on every
    screen -- Login in particular needs this before anyone has
    authenticated, and business_name isn't exposed by any
    unauthenticated endpoint (system_settings is superuser-gated, same
    as every other admin-configurable value). Set once by the Setup
    Wizard, and re-synced here whenever it's changed later through
    Settings (see the Settings business-name tab).
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    return settings.value(BUSINESS_NAME_KEY, "")


def save_business_name(name: str):
    """
    Persists this shop's display name for this machine.

    Args:
        name: The shop's display name.
    """
    settings = QSettings(ORG_NAME, APP_NAME)
    settings.setValue(BUSINESS_NAME_KEY, name)
