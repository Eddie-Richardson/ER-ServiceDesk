# ER-ServiceDesk/desktop/session.py
# In-memory session state for the currently logged-in user.
#
# The JWT lives here for the lifetime of the running app -- never written
# to disk. Any window that needs to make an authenticated API call imports
# this module and reads current_token(). Closing the app clears it, which
# is the correct behavior for a shared shop machine: nobody stays logged
# in after the app closes.

_access_token: str | None = None


def set_token(token: str):
    """Stores the access token for the current session."""
    global _access_token
    _access_token = token


def current_token() -> str | None:
    """Returns the current session's access token, or None if not logged in."""
    return _access_token


def clear():
    """Clears the current session, e.g. on logout."""
    global _access_token
    _access_token = None


def is_logged_in() -> bool:
    return _access_token is not None
