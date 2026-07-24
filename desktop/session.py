# ER-ServiceDesk/desktop/session.py

"""
In-memory session state for the currently logged-in user.

The JWT lives here for the lifetime of the running app -- never written
to disk. Any window that needs to make an authenticated API call imports
this module and reads current_token(). Closing the app clears it, which
is the correct behavior for a shared shop machine: nobody stays logged
in after the app closes.

The token's claims (is_superuser, permissions, email, full_name) are
decoded once at login and cached here for the UI to read -- e.g. to
decide whether to show the Inventory or Users & Roles nav items. This
is read-only, UI-convenience decoding with no signature check: the
client has no way to verify a JWT's signature without the backend's
SECRET_KEY, and it doesn't need to -- the backend independently
re-verifies and re-authorizes every request regardless of what the
client believes about its own token.
"""

import base64
import json

_access_token: str | None = None
_claims: dict = {}


def _decode_claims(token: str) -> dict:
    """
    Extracts the payload claims from a JWT without verifying its signature.
    Malformed tokens decode to an empty dict rather than raising, since
    this is only ever used for optional UI display/routing decisions.
    """
    try:
        payload_segment = token.split(".")[1]
        padding = "=" * (-len(payload_segment) % 4)
        decoded = base64.urlsafe_b64decode(payload_segment + padding)
        return json.loads(decoded)
    except (IndexError, ValueError, json.JSONDecodeError):
        return {}


def set_token(token: str):
    """Stores the access token for the current session and decodes its claims."""
    global _access_token, _claims
    _access_token = token
    _claims = _decode_claims(token)


def current_token() -> str | None:
    """Returns the current session's access token, or None if not logged in."""
    return _access_token


def clear():
    """Clears the current session, e.g. on logout."""
    global _access_token, _claims
    _access_token = None
    _claims = {}


def is_logged_in() -> bool:
    """
    Returns:
        Whether a session is currently active.
    """
    return _access_token is not None


def is_superuser() -> bool:
    """Returns whether the current session belongs to a superuser account."""
    return bool(_claims.get("is_superuser", False))


def current_permissions() -> set[str]:
    """
    Returns:
        The current session's effective permissions (e.g.
        {"tickets.manage", "customers.manage"}), computed server-side
        from the user's assigned roles at login time. Empty set if not
        logged in or the user holds no permission-granting roles.
    """
    return set(_claims.get("permissions", []))


def has_permission(permission_name: str) -> bool:
    """
    Checks whether the current session can perform an action gated by
    the given permission. Superusers always return True, before any
    permission lookup -- is_superuser is a full bypass, independent of
    the Role system, matching how the backend enforces it.

    Args:
        permission_name: The permission to check, e.g. "inventory.manage".

    Returns:
        Whether the current session holds this permission (directly or
        via the superuser bypass).
    """
    if is_superuser():
        return True
    return permission_name in current_permissions()


def current_email() -> str | None:
    """
    Returns:
        The current session's email address, or None if not logged in.
    """
    return _claims.get("email")


def current_full_name() -> str | None:
    """
    Returns:
        The current session's full name, or None if not logged in.
    """
    return _claims.get("full_name")


def current_user_id() -> int | None:
    """
    Returns the current session's own user id, decoded from the JWT's
    "sub" claim. Used for self-assignment -- an agent doesn't need the
    full technician list (which they may not have permission to fetch)
    to assign a ticket to themselves.

    Returns:
        The current user's id, or None if not logged in or the claim
        is missing/malformed.
    """
    sub = _claims.get("sub")
    if sub is None:
        return None
    try:
        return int(sub)
    except (TypeError, ValueError):
        return None
