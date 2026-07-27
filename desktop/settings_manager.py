# ER-ServiceDesk/desktop/settings_manager.py

"""
App settings, backed by QSettings, split across two scopes on purpose:

- Theme is a genuine per-person preference -- different employees
  logging into the same PC might reasonably want different themes --
  so it stays UserScope (HKEY_CURRENT_USER on Windows), writable by
  any account without needing admin rights.

- install_mode, backend_url, and business_name are facts about how
  this machine's copy of ER-ServiceDesk is set up, not about whoever
  happens to be logged in. They're now SystemScope (HKEY_LOCAL_MACHINE
  on Windows) -- readable by any account on the machine, but only
  writable by an admin. This matches how the installer itself now
  works (PrivilegesRequired=admin) and the real-world pattern this
  project is built around: Local installs are realistically a single
  shop owner who's already an admin on their own PC; Server is
  headless and only ever touched by IT/admin staff directly; Client is
  the one case with a genuinely non-admin regular employee, but Client
  never writes any of these three values at all -- it only reads the
  one install_mode/backend_url pair the installer already set for it.

QSettings stores data in the OS-native location automatically -- the
Windows registry on Windows, a plist on macOS, an ini file on Linux.
This gives us "remember this setting" without writing any
platform-specific code ourselves.
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

BUSINESS_NAME_KEY = "deployment/business_name"


def _user_settings() -> QSettings:
    """Returns a per-user QSettings instance, for genuine per-person preferences like theme."""
    return QSettings(ORG_NAME, APP_NAME)


def _machine_settings() -> QSettings:
    """
    Returns a machine-wide QSettings instance, for facts about how
    this machine's install is configured. Writing through this
    requires admin rights on Windows; reading does not.
    """
    return QSettings(QSettings.SystemScope, ORG_NAME, APP_NAME)


def get_saved_theme() -> str:
    """
    Returns the saved theme preference for the current user ("light" or
    "dark"). Falls back to the default if nothing has been saved yet, or
    if the stored value is somehow invalid.
    """
    value = _user_settings().value(THEME_KEY, DEFAULT_THEME)
    return value if value in ("light", "dark") else DEFAULT_THEME


def save_theme(theme_name: str):
    """
    Persists the given theme preference for the current user.

    Args:
        theme_name: Either "light" or "dark".
    """
    _user_settings().setValue(THEME_KEY, theme_name)


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
    value = _machine_settings().value(INSTALL_MODE_KEY, DEFAULT_INSTALL_MODE)
    return value if value in VALID_INSTALL_MODES else DEFAULT_INSTALL_MODE


def save_install_mode(mode: str):
    """
    Persists this machine's install mode. Requires admin rights on
    Windows, since this is now a machine-wide (SystemScope) setting.

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
    _machine_settings().setValue(INSTALL_MODE_KEY, mode)


def get_backend_url() -> str:
    """
    Returns the backend URL this machine should talk to. Defaults to
    localhost for Local/Server mode (where the backend runs on this
    same machine); Client mode installs save a real network address
    here instead, pointed at whichever machine is running Server mode.
    """
    return _machine_settings().value(BACKEND_URL_KEY, DEFAULT_BACKEND_URL)


def save_backend_url(url: str):
    """
    Persists the backend URL this machine should talk to. Requires
    admin rights on Windows, since this is now a machine-wide
    (SystemScope) setting.

    Args:
        url: A full base URL, e.g. "http://localhost:8000" or
            "http://192.168.1.50:8000". No trailing slash.
    """
    _machine_settings().setValue(BACKEND_URL_KEY, url)


def get_business_name() -> str:
    """
    Returns this shop's display name, as set during installation.
    Empty string if never set.

    Cached locally rather than fetched from the backend on every
    screen -- Login in particular needs this before anyone has
    authenticated, and business_name isn't exposed by any
    unauthenticated endpoint (system_settings is superuser-gated, same
    as every other admin-configurable value). Set once by the
    installer, and re-synced here whenever it's changed later through
    Settings (see the Settings business-name tab).
    """
    return _machine_settings().value(BUSINESS_NAME_KEY, "")


def save_business_name(name: str):
    """
    Persists this shop's display name for this machine. Requires admin
    rights on Windows, since this is now a machine-wide (SystemScope)
    setting.

    Args:
        name: The shop's display name.
    """
    _machine_settings().setValue(BUSINESS_NAME_KEY, name)
