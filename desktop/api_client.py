# ER-ServiceDesk/desktop/api_client.py

"""
Thin API client for talking to the FastAPI backend.

Kept deliberately small: right now it only knows how to log in and fetch
tickets/ticket statuses. As more windows need the API (Inventory,
Customers, etc.) they can add their own request functions here, all
sharing BASE_URL and the same error-handling shape established below.
"""

import requests

from desktop import session
from desktop.settings_manager import get_backend_url

# Initialized from whatever was last saved (defaults to localhost for a
# normal Local-mode install). A Client-mode install saves a real network
# address instead -- see settings_manager.save_backend_url(). Mutable at
# runtime via set_base_url(), rather than a one-time constant, so the
# Setup Wizard can change it without restarting the app, and so a
# Local-to-Server migration can repoint an existing install later.
BASE_URL = get_backend_url()


def set_base_url(url: str):
    """
    Changes which backend this client talks to, immediately, for the
    rest of the running session. Does not persist anything itself --
    call settings_manager.save_backend_url() separately if the change
    should survive a restart.

    Args:
        url: A full base URL, e.g. "http://localhost:8000" or
            "http://192.168.1.50:8000". No trailing slash.
    """
    global BASE_URL
    BASE_URL = url


class LoginError(Exception):
    """
    Raised when login fails for a reason the person can act on --
    wrong credentials, or the backend being unreachable. The message is
    written to be shown directly in the UI.
    """
    pass


class MustChangePasswordError(LoginError):
    """
    Raised when credentials are valid but the account's password was
    set by an admin (a new account, or a Reset Password action) and
    must be changed before the person can do anything else. Carries
    the email so the caller can pre-fill the password-change screen
    without asking the person to retype it.
    """

    def __init__(self, email: str):
        self.email = email
        super().__init__("You must set a new password before continuing.")


class ApiError(Exception):
    """
    Raised when an authenticated request fails. The message is written
    to be shown directly in the UI.
    """
    pass


def _authed_get(path: str) -> list | dict:
    """
    Performs a GET request against the backend with the current session's
    bearer token attached.

    Args:
        path: Path relative to BASE_URL, e.g. "/tickets/".

    Returns:
        The parsed JSON response body.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the response isn't a success.
    """
    token = session.current_token()
    if not token:
        raise ApiError("No active session. Please log in again.")

    try:
        response = requests.get(
            f"{BASE_URL}{path}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise ApiError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")

    if response.status_code != 200:
        raise ApiError(f"Request failed (server returned {response.status_code}).")

    return response.json()


def _authed_post(path: str, payload: dict) -> dict:
    """
    Performs a POST request against the backend with the current
    session's bearer token attached.

    Args:
        path: Path relative to BASE_URL, e.g. "/tickets/".
        payload: The JSON body to send.

    Returns:
        The parsed JSON response body.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the response isn't a success.
    """
    return _authed_write("POST", path, payload)


def _authed_put(path: str, payload: dict) -> dict:
    """
    Performs a PUT request against the backend with the current
    session's bearer token attached.

    Args:
        path: Path relative to BASE_URL, e.g. "/tickets/5".
        payload: The JSON body to send.

    Returns:
        The parsed JSON response body.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the response isn't a success.
    """
    return _authed_write("PUT", path, payload)


def _authed_write(method: str, path: str, payload: dict) -> dict:
    """
    Shared implementation for _authed_post and _authed_put.

    Args:
        method: "POST" or "PUT".
        path: Path relative to BASE_URL.
        payload: The JSON body to send.

    Returns:
        The parsed JSON response body.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the response isn't a success.
    """
    token = session.current_token()
    if not token:
        raise ApiError("No active session. Please log in again.")

    try:
        response = requests.request(
            method,
            f"{BASE_URL}{path}",
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise ApiError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")

    if response.status_code not in (200, 201):
        detail = ""
        try:
            body = response.json()
            # The backend's real shape is {"error": {"code", "message"}} --
            # never "detail". This was previously checking for "detail",
            # which doesn't exist anywhere in this API, so every specific
            # backend error message silently fell back to the generic
            # "server returned N" text below instead of ever being shown.
            detail = body.get("error", {}).get("message", "")
        except ValueError:
            pass
        raise ApiError(detail or f"Request failed (server returned {response.status_code}).")

    return response.json()


def list_tickets() -> list[dict]:
    """Returns all tickets. Requires an active session."""
    return _authed_get("/tickets/")


def list_ticket_statuses() -> list[dict]:
    """Returns all ticket statuses (id, name, description). Requires an active session."""
    return _authed_get("/ticket_statuses/")


def list_ticket_categories() -> list[dict]:
    """Returns all ticket categories (id, name, description). Requires an active session."""
    return _authed_get("/ticket_categories/")


def list_ticket_types() -> list[dict]:
    """Returns all ticket types (id, name, description). Requires an active session."""
    return _authed_get("/ticket_types/")


def list_customers() -> list[dict]:
    """Returns all customers. Requires an active session."""
    return _authed_get("/customers/")


def list_devices() -> list[dict]:
    """Returns all devices. Requires an active session."""
    return _authed_get("/devices/")


def list_users() -> list[dict]:
    """
    Returns all user accounts. Requires an active session belonging to a
    superuser -- the backend's /users router is superuser-gated. Callers
    should check session.is_superuser() before calling this, and treat a
    failure here as non-fatal: regular agents fall back to self-assignment
    only, which needs no call to this function at all.
    """
    return _authed_get("/users/")


def list_roles() -> list[dict]:
    """Returns all roles. Requires a superuser session (backend is superuser-gated)."""
    return _authed_get("/roles/")


def list_user_roles() -> list[dict]:
    """
    Returns every user-role assignment in the system (id, user_id,
    role_id). Not filterable server-side; callers filter by user_id
    client-side against the already-fetched full list. Requires a
    superuser session.
    """
    return _authed_get("/user_roles/")


def create_user(payload: dict) -> dict:
    """
    Creates a new user account.

    Args:
        payload: Fields matching the backend's UserCreate schema
            (email, first_name, last_name, password required;
            is_active/is_superuser optional).

    Returns:
        The created user record.
    """
    return _authed_post("/users/", payload)


def update_user(user_id: int, payload: dict) -> dict:
    """
    Updates an existing user account.

    Args:
        user_id: The user's id.
        payload: Fields to update, matching UserUpdate. Password
            changes never go through this function -- see
            reset_user_password() for admin-initiated resets.

    Returns:
        The updated user record.
    """
    return _authed_put(f"/users/{user_id}", payload)


def reset_user_password(user_id: int) -> dict:
    """
    Generates and emails a new temporary password for an existing user,
    forcing them to set their own on next login. The admin never sees
    or chooses the new password.

    Args:
        user_id: The user whose password is being reset.

    Returns:
        The updated user record.
    """
    return _authed_post(f"/users/{user_id}/reset-password", {})


def create_user_role(user_id: int, role_id: int) -> dict:
    """
    Assigns a role to a user.

    Args:
        user_id: The user to grant the role to.
        role_id: The role being granted.

    Returns:
        The created user-role link record.
    """
    return _authed_post("/user_roles/", {"user_id": user_id, "role_id": role_id})


def delete_user_role(user_role_id: int):
    """
    Removes a role from a user.

    Args:
        user_role_id: The id of the specific user-role LINK record to
            remove (not the user's id or the role's id -- the join
            record's own id, as returned by list_user_roles()).
    """
    token = session.current_token()
    if not token:
        raise ApiError("No active session. Please log in again.")

    try:
        response = requests.delete(
            f"{BASE_URL}/user_roles/{user_role_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise ApiError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")
    if response.status_code not in (200, 204):
        raise ApiError(f"Request failed (server returned {response.status_code}).")


def create_ticket(payload: dict) -> dict:
    """
    Creates a new ticket.

    Args:
        payload: Fields matching the backend's TicketCreate schema
            (customer_id, device_id, category_id, type_id, status_id,
            title, priority, and optionally description/assigned_to).

    Returns:
        The created ticket record.
    """
    return _authed_post("/tickets/", payload)


def create_device(payload: dict) -> dict:
    """
    Creates a new device.

    Args:
        payload: Fields matching the backend's DeviceCreate schema
            (customer_id, device_type, and optionally brand/model/
            serial_number).

    Returns:
        The created device record.
    """
    return _authed_post("/devices/", payload)


def update_ticket(ticket_id: int, payload: dict) -> dict:
    """
    Updates an existing ticket.

    Args:
        ticket_id: The ticket's id.
        payload: Fields to update, matching the backend's TicketUpdate
            schema. Only include fields that changed.

    Returns:
        The updated ticket record.
    """
    return _authed_put(f"/tickets/{ticket_id}", payload)


def list_locations() -> list[dict]:
    """Returns all locations. Requires an active session."""
    return _authed_get("/inventory/locations/")


def create_customer(payload: dict) -> dict:
    """
    Creates a new customer.

    Args:
        payload: Fields matching the backend's CustomerCreate schema
            (first_name, last_name, email required; phone/address
            optional).

    Returns:
        The created customer record.
    """
    return _authed_post("/customers/", payload)


def update_customer(customer_id: int, payload: dict) -> dict:
    """
    Updates an existing customer.

    Args:
        customer_id: The customer's id.
        payload: Fields to update, matching the backend's CustomerUpdate
            schema. Only include fields that changed.

    Returns:
        The updated customer record.
    """
    return _authed_put(f"/customers/{customer_id}", payload)


def update_device(device_id: int, payload: dict) -> dict:
    """
    Updates an existing device.

    Args:
        device_id: The device's id.
        payload: Fields to update, matching the backend's DeviceUpdate
            schema. Only include fields that changed.

    Returns:
        The updated device record.
    """
    return _authed_put(f"/devices/{device_id}", payload)


def list_asset_categories() -> list[dict]:
    """Returns all asset categories (id, name, description). Requires an active session."""
    return _authed_get("/inventory/asset_categories/")


def list_assets() -> list[dict]:
    """
    Returns all assets. Requires an active session.

    The backend paginates this endpoint (a holdover from the original
    InventoryHub API it was merged from), returning {"items": [...],
    ...page metadata}. A shop's own asset inventory is small enough that
    the desktop app just requests everything in one page rather than
    building real pagination UI for it.
    """
    response = _authed_get("/inventory/assets/?limit=1000")
    return response["items"]


def create_asset(payload: dict) -> dict:
    """
    Creates a new asset.

    Args:
        payload: Fields matching the backend's AssetCreate schema (name
            required; sku/category_id/manufacturer/model/serial_number/
            status/location_id/price/purchase_date/warranty_expiration/
            assigned_to/condition/notes all optional).

    Returns:
        The created asset record. The backend wraps this in
        {"message": ..., "asset": {...}}; this function unwraps it so
        callers get the record directly, consistent with every other
        create_* function here.
    """
    response = _authed_post("/inventory/assets/", payload)
    return response["asset"]


def update_asset(asset_id: int, payload: dict) -> dict:
    """
    Updates an existing asset.

    Args:
        asset_id: The asset's id.
        payload: Fields to update, matching the backend's AssetUpdate
            schema. Only include fields that changed.

    Returns:
        The updated asset record.
    """
    return _authed_put(f"/inventory/assets/{asset_id}", payload)


def list_parts() -> list[dict]:
    """Returns all parts. Requires an active session."""
    return _authed_get("/inventory/parts/")


def list_low_stock_parts() -> list[dict]:
    """Returns every part currently at or below its reorder threshold. Requires an active session."""
    return _authed_get("/inventory/parts/low-stock")


def create_part(payload: dict) -> dict:
    """
    Creates a new part.

    Args:
        payload: Fields matching the backend's PartCreate schema (name
            required; sku/reorder_threshold/unit_cost/supplier/notes
            all optional; locations is an optional list of
            {"location_id": int, "quantity": int} entries describing
            the part's initial stock breakdown across locations).

    Returns:
        The created part record.
    """
    return _authed_post("/inventory/parts/", payload)


def update_part(part_id: int, payload: dict) -> dict:
    """
    Updates an existing part.

    Args:
        part_id: The part's id.
        payload: Fields to update, matching the backend's PartUpdate
            schema. Only include fields that changed.

    Returns:
        The updated part record.
    """
    return _authed_put(f"/inventory/parts/{part_id}", payload)


def login(email: str, password: str) -> str:
    """
    Authenticates against POST /auth/login and returns the access token.

    Args:
        email: The user's email address.
        password: The user's plaintext password.

    Returns:
        The JWT access token string.

    Raises:
        LoginError: If credentials are invalid or the backend can't be
            reached. The exception message is safe to display as-is.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise LoginError(
            "Couldn't reach the backend. Make sure it's still running."
        )

    if response.status_code == 400:
        raise LoginError("Incorrect email or password.")

    if response.status_code != 200:
        raise LoginError(f"Login failed (server returned {response.status_code}).")

    data = response.json()
    if data.get("must_change_password"):
        raise MustChangePasswordError(email)

    token = data.get("access_token")
    if not token:
        raise LoginError("Login succeeded but no access token was returned.")

    return token


def change_password(email: str, current_password: str, new_password: str) -> str:
    """
    Sets a new password for an account whose login was blocked by
    must_change_password. Deliberately unauthenticated -- the person
    calling this has no token yet, since that's exactly the situation
    this function resolves. Re-verifies current_password server-side.

    Args:
        email: The account's email.
        current_password: The temp (or old) password, re-verified
            server-side before anything changes.
        new_password: The new password to set.

    Returns:
        A fresh access token, so the person is logged in immediately
        after changing their password rather than needing to log in
        again separately.

    Raises:
        LoginError: If current_password is wrong, new_password fails
            validation (too short, or over bcrypt's byte limit), or the
            backend can't be reached. The message is safe to display
            as-is.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/auth/change-password",
            json={
                "email": email,
                "current_password": current_password,
                "new_password": new_password,
            },
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise LoginError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code != 200:
        message = ""
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            pass
        raise LoginError(message or f"Couldn't change the password (server returned {response.status_code}).")

    token = response.json().get("access_token")
    if not token:
        raise LoginError("Password changed but no access token was returned.")

    return token


# ---------------------------------------------------------------------------
# Generic lookup-table CRUD (Settings window)
# ---------------------------------------------------------------------------
# Locations, Asset Categories, Ticket Categories, Ticket Statuses, and
# Ticket Types are all the same shape now (name + description) -- rather
# than five near-identical named function sets, Settings' reusable
# LookupTab passes its own endpoint path into these generic functions.
# The existing named list_* functions elsewhere (list_locations() etc.,
# used by Tickets/Inventory for dropdowns) are untouched by this.

def create_lookup_item(endpoint: str, payload: dict) -> dict:
    """
    Creates a new record in a simple name/description lookup table.

    Args:
        endpoint: The resource path, e.g. "/inventory/locations/".
        payload: {"name": str, "description": str | None}.

    Returns:
        The created record.
    """
    return _authed_post(endpoint, payload)


def update_lookup_item(endpoint: str, item_id: int, payload: dict) -> dict:
    """
    Updates an existing record in a simple name/description lookup table.

    Args:
        endpoint: The resource path, e.g. "/inventory/locations/".
        item_id: The record's id.
        payload: Fields to update.

    Returns:
        The updated record.
    """
    return _authed_put(f"{endpoint}{item_id}", payload)


def delete_lookup_item(endpoint: str, item_id: int):
    """
    Deletes a record from a simple name/description lookup table.

    Args:
        endpoint: The resource path, e.g. "/inventory/locations/".
        item_id: The record's id.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the delete fails -- including if the backend
            rejects it because the record is still referenced elsewhere
            (e.g. a Location still assigned to existing tickets).
    """
    token = session.current_token()
    if not token:
        raise ApiError("No active session. Please log in again.")

    try:
        response = requests.delete(
            f"{BASE_URL}{endpoint}{item_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise ApiError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")
    if response.status_code not in (200, 204):
        message = ""
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            pass
        raise ApiError(message or f"Delete failed (server returned {response.status_code}).")


# ---------------------------------------------------------------------------
# Roles & Permissions (Settings window)
# ---------------------------------------------------------------------------

def list_permissions() -> list[dict]:
    """
    Returns every permission that exists in the system. Read-only from
    the desktop app's perspective -- permissions are hardcoded into
    specific backend routes as the actual enforcement mechanism, so
    creating a new one through the UI wouldn't gate anything without a
    developer also wiring it into code. Roles bundle existing
    permissions together; Settings doesn't let anyone invent new ones.
    """
    return _authed_get("/permissions/")


def create_role(payload: dict) -> dict:
    """
    Creates a new role.

    Args:
        payload: {"name": str, "description": str | None}.

    Returns:
        The created role record.
    """
    return _authed_post("/roles/", payload)


def update_role(role_id: int, payload: dict) -> dict:
    """
    Updates an existing role's name/description (not its permissions --
    see create_role_permission/delete_role_permission for that).

    Args:
        role_id: The role's id.
        payload: Fields to update.

    Returns:
        The updated role record.
    """
    return _authed_put(f"/roles/{role_id}", payload)


def delete_role(role_id: int):
    """
    Deletes a role by id.

    Args:
        role_id: The role's id.

    Raises:
        ApiError: If the delete fails, including if users are still
            assigned this role.
    """
    delete_lookup_item("/roles/", role_id)


def create_role_permission(role_id: int, permission_id: int) -> dict:
    """
    Grants a permission to a role.

    Args:
        role_id: The role being granted the permission.
        permission_id: The permission being granted.

    Returns:
        The created role-permission link record.
    """
    return _authed_post("/role_permissions/", {"role_id": role_id, "permission_id": permission_id})


def delete_role_permission(role_permission_id: int):
    """
    Revokes a permission from a role.

    Args:
        role_permission_id: The id of the specific role-permission LINK
            record to remove (not the role's id or the permission's id
            -- the join record's own id, as returned by the role's
            role_permissions list).
    """
    delete_lookup_item("/role_permissions/", role_permission_id)


# ---------------------------------------------------------------------------
# Record locking (check-out style edit locks)
# ---------------------------------------------------------------------------

class LockConflictError(ApiError):
    """
    Raised when a record is already locked by someone else. Carries the
    human-readable message from the backend (which names who holds it)
    so it can be shown directly to the user without extra formatting.
    """
    pass


def acquire_lock(entity_type: str, entity_id: int) -> dict:
    """
    Attempts to acquire a check-out lock on a record before opening it
    for editing.

    Args:
        entity_type: The kind of record, e.g. "ticket", "customer".
        entity_id: The record's own primary key.

    Returns:
        The lock record.

    Raises:
        LockConflictError: If someone else currently holds a non-stale
            lock on this record. The message names who.
        ApiError: For any other failure (session expired, backend
            unreachable, etc.).
    """
    token = session.current_token()
    if not token:
        raise ApiError("No active session. Please log in again.")

    try:
        response = requests.post(
            f"{BASE_URL}/locks/acquire",
            json={"entity_type": entity_type, "entity_id": entity_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        raise ApiError("Couldn't reach the backend. Make sure it's still running.")

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")

    if response.status_code == 409:
        message = ""
        try:
            message = response.json().get("error", {}).get("message", "")
        except ValueError:
            pass
        raise LockConflictError(message or "This record is currently being edited by someone else.")

    if response.status_code != 200:
        raise ApiError(f"Couldn't lock the record (server returned {response.status_code}).")

    return response.json()


def release_lock(entity_type: str, entity_id: int):
    """
    Releases a check-out lock, if the current session holds it.

    Deliberately quiet about most failure modes -- this is called when
    a dialog is already closing, so there's nothing useful left to show
    the user if the release itself has a network hiccup. Session-expiry
    is the one case worth raising, since it's a real, actionable signal.

    Args:
        entity_type: The kind of record, e.g. "ticket", "customer".
        entity_id: The record's own primary key.

    Raises:
        ApiError: Only if the session has expired.
    """
    token = session.current_token()
    if not token:
        return

    try:
        response = requests.post(
            f"{BASE_URL}/locks/release",
            json={"entity_type": entity_type, "entity_id": entity_id},
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except requests.exceptions.RequestException:
        return

    if response.status_code == 401:
        raise ApiError("Session expired. Please log in again.")
