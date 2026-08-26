# ER-ServiceDesk/desktop/api_client.py

"""
API client for talking to the FastAPI backend -- one thin wrapper
function per endpoint, covering every feature area the desktop app
uses (tickets, customers, devices, inventory, billing, users/roles,
and more). Every function shares BASE_URL and the same
error-handling shape established below.
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


class SessionExpiredError(ApiError):
    """
    Raised specifically when the backend rejects a request with 401 --
    distinct from ApiError so a single, central handler (see
    desktop/base_dialog.py) can catch this one case and force a
    logout, rather than every individual dialog needing its own check.
    """
    pass


def fetch_business_name() -> str:
    """
    Fetches the shop's display name from the server. Requires an
    active, authenticated session -- see app/routes/business_info.py
    server-side; there is no unauthenticated way to reach this at all.
    Called right after a successful login (see login_window.py) to
    cache this locally, since a Client machine never collects it
    during its own install the way Local/Server do.

    Never raises -- this is a nice-to-have branding fetch, not
    something that should ever block or break the login flow. Any
    failure (server unreachable, bad response, etc.) just returns an
    empty string, same as if no business name were configured at all.

    Returns:
        The business name, or "" on any failure.
    """
    try:
        result = _authed_get("/business-info/business-name")
        return result.get("business_name", "") or ""
    except ApiError:
        return ""


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
        raise SessionExpiredError("Session expired. Please log in again.")

    if response.status_code != 200:
        raise ApiError(f"Request failed (server returned {response.status_code}).")

    return response.json()


def _authed_post(path: str, payload: dict) -> dict:
    return _authed_write("POST", path, payload)


def _authed_put(path: str, payload: dict) -> dict:
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
        raise SessionExpiredError("Session expired. Please log in again.")

    if response.status_code not in (200, 201):
        detail = ""
        try:
            body = response.json()
            # The backend's real shape is {"error": {"code", "message"}} --
            # never "detail". Checking for "detail" instead would mean
            # every specific backend error message silently falls back
            # to the generic "server returned N" text below instead of
            # ever being shown.
            detail = body.get("error", {}).get("message", "")
        except ValueError:
            pass
        raise ApiError(detail or f"Request failed (server returned {response.status_code}).")

    return response.json()


def send_waiver(ticket_id: int) -> dict:
    """Emails the liability waiver to this ticket's customer, and returns the updated ticket with waiver_sent_at set."""
    return _authed_post(f"/tickets/{ticket_id}/send-waiver", {})


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


def list_ticket_stages() -> list[dict]:
    """Returns all ticket stages (id, name, description). Requires an active session."""
    return _authed_get("/ticket_stages/")


def list_stages_for_type(type_id: int) -> list[dict]:
    """
    Returns every (type, stage) allow-list entry for a single ticket
    type -- which stages are currently allowed for it.
    """
    return _authed_get(f"/ticket_type_stages/by-type/{type_id}")


def create_ticket_type_stage(type_id: int, stage_id: int) -> dict:
    """Allows a stage for a ticket type."""
    return _authed_post("/ticket_type_stages/", {"type_id": type_id, "stage_id": stage_id})


def delete_ticket_type_stage(ticket_type_stage_id: int):
    """
    Removes a stage from a ticket type's allow-list.

    Args:
        ticket_type_stage_id: The allow-list entry's own id (not the
            type or stage id).
    """
    delete_lookup_item("/ticket_type_stages/", ticket_type_stage_id)


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


def list_assignable_users() -> list[dict]:
    """
    Returns every active user's {"id", "full_name", "is_front_desk"} --
    available to any authenticated user, not just superusers. Used to
    both resolve a ticket's assigned_to for display, and populate the
    "Assigned To" picker, without requiring superuser access the way
    the full list_users() does.
    """
    return _authed_get("/users/assignable")


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
    Args:
        payload: Fields matching the backend's UserCreate schema
            (email, first_name, last_name, password required;
            is_active/is_superuser optional).
    """
    return _authed_post("/users/", payload)


def update_user(user_id: int, payload: dict) -> dict:
    """
    Args:
        payload: Fields to update, matching UserUpdate. Password
            changes never go through this function -- see
            reset_user_password() for admin-initiated resets.
    """
    return _authed_put(f"/users/{user_id}", payload)


def reset_user_password(user_id: int) -> dict:
    """
    Generates and emails a new temporary password for an existing user,
    forcing them to set their own on next login. The admin never sees
    or chooses the new password.
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
        raise SessionExpiredError("Session expired. Please log in again.")
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

    The backend paginates this endpoint, returning {"items": [...],
    ...page metadata}. A shop's own asset inventory is small enough
    that the desktop app just requests everything in one page rather
    than building real pagination UI for it.
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
        payload: Fields to update, matching the backend's AssetUpdate
            schema. Only include fields that changed.

    Returns:
        The updated asset record.
    """
    return _authed_put(f"/inventory/assets/{asset_id}", payload)


def list_parts() -> list[dict]:
    """Returns all parts. Requires an active session."""
    return _authed_get("/inventory/parts/")


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


def heartbeat() -> str:
    """
    Calls POST /auth/heartbeat and returns the freshly-renewed access
    token. Called by activity_monitor.py on genuine, detected user
    activity, not on a fixed schedule -- see that module for the real
    trigger logic.

    Returns:
        The new JWT access token string.

    Raises:
        ApiError: If there's no active session, the backend can't be
            reached, or the response isn't a success -- e.g. the
            session already genuinely expired before this call fired.
    """
    data = _authed_post("/auth/heartbeat", {})
    return data["access_token"]


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
        payload: Fields to update.

    Returns:
        The updated record.
    """
    return _authed_put(f"{endpoint}{item_id}", payload)


def delete_device(device_id: int):
    """
    Deletes a device by id.

    Raises:
        ApiError: If the device is currently attached to a ticket --
            see device_service.delete() server-side for the exact rule.
    """
    delete_lookup_item("/devices/", device_id)


def archive_customer(customer_id: int) -> dict:
    """
    Archives a customer -- hides them from the active ticket picker
    and the default Customers view. Fully reversible.
    """
    return _authed_post(f"/customers/{customer_id}/archive", {})


def unarchive_customer(customer_id: int) -> dict:
    """Reverses archive_customer()."""
    return _authed_post(f"/customers/{customer_id}/unarchive", {})


def delete_customer(customer_id: int):
    """
    Deletes a customer by id.

    Raises:
        ApiError: If the customer has any tickets or devices on file --
            see customer_service.delete() server-side for the exact rule.
    """
    delete_lookup_item("/customers/", customer_id)


def delete_lookup_item(endpoint: str, item_id: int):
    """
    Deletes a record from a simple name/description lookup table.

    Args:
        endpoint: The resource path, e.g. "/inventory/locations/".

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
        raise SessionExpiredError("Session expired. Please log in again.")
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
        payload: Fields to update.

    Returns:
        The updated role record.
    """
    return _authed_put(f"/roles/{role_id}", payload)


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
        raise SessionExpiredError("Session expired. Please log in again.")

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
        raise SessionExpiredError("Session expired. Please log in again.")


def list_messages_for_ticket(ticket_id: int) -> list[dict]:
    """
    Returns every entry in a ticket's note/conversation history --
    internal notes and customer email exchange together -- in
    whatever order the backend returns them (creation order). Visible
    to anyone with ticket access -- shared history, not private to
    its author.

    Args:
        ticket_id: The ticket to fetch entries for.
    """
    all_messages = _authed_get("/messages/")
    return [m for m in all_messages if m.get("ticket_id") == ticket_id]


def create_message(payload: dict) -> dict:
    """
    Creates a new entry. If payload's direction is "outbound", the
    backend also emails the content to the customer -- see
    message_service.create() server-side.

    Args:
        payload: Fields matching the backend's MessageCreate schema
            (ticket_id, user_id, customer_id, direction, content).

    Returns:
        The created record.
    """
    return _authed_post("/messages/", payload)


def update_message(message_id: int, payload: dict) -> dict:
    """
    Edits an existing entry's content.

    Args:
        payload: {"content": "..."} -- the only field an edit can
            change (see MessageUpdate server-side).

    Returns:
        The updated record.

    Raises:
        ApiError: 403 if the current user isn't allowed to edit this
            specific entry (see message_service.update() server-side
            for the exact rule).
    """
    return _authed_put(f"/messages/{message_id}", payload)


def delete_message(message_id: int):
    """
    Deletes an entry by id.

    Raises:
        ApiError: 403 if the current user isn't allowed to delete this
            specific entry (see message_service.delete() server-side
            for the exact rule).
    """
    delete_lookup_item("/messages/", message_id)


def list_status_history_for_ticket(ticket_id: int) -> list[dict]:
    """
    Returns a ticket's full status change history, in whatever order
    the backend returns them (creation order -- oldest first).
    Read-only; there's no create/update/delete for this at all, since
    entries are only ever written internally by the backend when a
    status genuinely changes.

    Args:
        ticket_id: The ticket to fetch history for.
    """
    all_entries = _authed_get("/status_histories/")
    return [e for e in all_entries if e.get("ticket_id") == ticket_id]


def list_ticket_parts_for_ticket(ticket_id: int) -> list[dict]:
    """
    Returns every part requirement on a single ticket, filtered
    server-side -- the overall ticket_parts table can grow large
    across every ticket over time, even though any one ticket only
    ever has a handful.

    Args:
        ticket_id: The ticket to fetch parts for.
    """
    return _authed_get(f"/ticket_parts/?ticket_id={ticket_id}")


def create_ticket_part(payload: dict) -> dict:
    """
    Creates a new part requirement on a ticket.

    Args:
        payload: {"ticket_id", "part_id", "quantity_needed", "status",
            "carrier", "tracking_number", "notes"} -- ticket_id and
            part_id are required, the rest optional.

    Returns:
        The newly created record.
    """
    return _authed_post("/ticket_parts/", payload)


def update_ticket_part(ticket_part_id: int, payload: dict) -> dict:
    """
    Updates an existing part requirement. If status actually changes,
    the backend automatically enqueues a customer notification -- see
    ticket_part_service.update() server-side.

    Args:
        payload: Fields to change; unset fields are left untouched.

    Returns:
        The updated record.
    """
    return _authed_put(f"/ticket_parts/{ticket_part_id}", payload)


def delete_ticket_part(ticket_part_id: int):
    """Deletes a part requirement by id."""
    delete_lookup_item("/ticket_parts/", ticket_part_id)


def list_quotes() -> list[dict]:
    """Returns every quote across the whole business. Requires billing_access."""
    return _authed_get("/quotes/")


def send_invoice(invoice_id: int) -> dict:
    """Emails this invoice to its ticket's customer, and returns the updated invoice with invoice_sent_at set. Sendable even after is_paid -- serves as a receipt."""
    return _authed_post(f"/invoices/{invoice_id}/send", {})


def list_invoices() -> list[dict]:
    """Returns every invoice across the whole business. Requires billing_access."""
    return _authed_get("/invoices/")


def list_quotes_for_ticket(ticket_id: int) -> list[dict]:
    """Returns every quote for a single ticket, filtered server-side. Requires billing_access."""
    return _authed_get(f"/quotes/?ticket_id={ticket_id}")


def create_quote(ticket_id: int) -> dict:
    """
    Creates a new, empty quote for a ticket -- use add_quote_line_item()
    to build it up afterward.
    """
    return _authed_post("/quotes/", {"ticket_id": ticket_id})


def get_quote(quote_id: int) -> dict:
    """Fetches a single quote by id, including its line items."""
    return _authed_get(f"/quotes/{quote_id}")


def update_quote(quote_id: int, payload: dict) -> dict:
    """
    Updates a quote's discount/tax selection or details. Changing
    discount_id/tax_rate_id recalculates totals server-side.
    """
    return _authed_put(f"/quotes/{quote_id}", payload)


def add_quote_line_item(quote_id: int, quantity: int, service_id: int | None = None, part_id: int | None = None) -> dict:
    """Adds a line item to a quote -- exactly one of service_id/part_id -- snapshotting its current name/price server-side."""
    params = f"service_id={service_id}" if service_id is not None else f"part_id={part_id}"
    return _authed_post(f"/quotes/{quote_id}/line-items?{params}&quantity={quantity}", {})


def update_quote_line_item(line_item_id: int, quantity: int) -> dict:
    """Updates a quote line item's quantity."""
    return _authed_put(f"/quotes/line-items/{line_item_id}", {"quantity": quantity})


def remove_quote_line_item(line_item_id: int):
    """Removes a line item from a quote."""
    delete_lookup_item("/quotes/line-items/", line_item_id)


def send_quote(quote_id: int) -> dict:
    """Emails this quote to its ticket's customer, and returns the updated quote with quote_sent_at set."""
    return _authed_post(f"/quotes/{quote_id}/send", {})


def delete_quote(quote_id: int):
    """
    Deletes a quote outright.

    Raises:
        ApiError: If it has line items, has already been sent, has
            already been converted to an invoice, or isn't the most
            recently created quote -- see quote_service.delete()
            server-side for the exact rules.
    """
    delete_lookup_item("/quotes/", quote_id)


def convert_quote_to_invoice(quote_id: int) -> dict:
    """Converts an approved quote into a real invoice, copying its line items and discount/tax selection."""
    return _authed_post(f"/quotes/{quote_id}/convert-to-invoice", {})


def list_invoices_for_ticket(ticket_id: int) -> list[dict]:
    """Returns every invoice for a single ticket, filtered server-side. Requires billing_access."""
    return _authed_get(f"/invoices/?ticket_id={ticket_id}")


def create_invoice(ticket_id: int) -> dict:
    """Creates a new, empty invoice for a ticket directly (not via quote conversion)."""
    return _authed_post("/invoices/", {"ticket_id": ticket_id})


def get_invoice(invoice_id: int) -> dict:
    """Fetches a single invoice by id, including its line items."""
    return _authed_get(f"/invoices/{invoice_id}")


def update_invoice(invoice_id: int, payload: dict) -> dict:
    """Updates an invoice's discount/tax selection, details, or is_paid."""
    return _authed_put(f"/invoices/{invoice_id}", payload)


def add_invoice_line_item(invoice_id: int, quantity: int, service_id: int | None = None, part_id: int | None = None) -> dict:
    """Adds a line item to an invoice -- exactly one of service_id/part_id -- snapshotting its current name/price server-side. A part line item deducts real inventory."""
    params = f"service_id={service_id}" if service_id is not None else f"part_id={part_id}"
    return _authed_post(f"/invoices/{invoice_id}/line-items?{params}&quantity={quantity}", {})


def update_invoice_line_item(line_item_id: int, quantity: int) -> dict:
    """Updates an invoice line item's quantity."""
    return _authed_put(f"/invoices/line-items/{line_item_id}", {"quantity": quantity})


def remove_invoice_line_item(line_item_id: int):
    """Removes a line item from an invoice."""
    delete_lookup_item("/invoices/line-items/", line_item_id)


def delete_invoice(invoice_id: int):
    """
    Deletes an invoice outright.

    Raises:
        ApiError: If it has line items, has already been sent, is
            marked paid or has payments recorded, came from a
            converted quote, or isn't the most recently created
            invoice -- see invoice_service.delete() server-side for
            the exact rules.
    """
    delete_lookup_item("/invoices/", invoice_id)


def list_payments_for_invoice(invoice_id: int) -> list[dict]:
    """Returns every payment recorded against a single invoice, filtered server-side."""
    return _authed_get(f"/payments/?invoice_id={invoice_id}")


def create_payment(invoice_id: int, amount: str, method: str) -> dict:
    """Records a payment against an invoice. Automatically marks it paid if this brings total payments up to its total."""
    return _authed_post("/payments/", {"invoice_id": invoice_id, "amount": amount, "method": method})


def create_payment_plan(invoice_id: int, installment_amount: str, frequency: str, start_date: str) -> dict:
    """Sets up a new payment plan on an invoice -- the number of installments and their due dates are worked out server-side."""
    return _authed_post("/payment_plans/", {
        "invoice_id": invoice_id, "installment_amount": installment_amount,
        "frequency": frequency, "start_date": start_date,
    })


def get_payment_plan_by_invoice(invoice_id: int) -> dict | None:
    """Fetches the payment plan for a given invoice, if any."""
    return _authed_get(f"/payment_plans/by-invoice/{invoice_id}")


def record_installment_payment(installment_id: int, amount: str | None, method: str) -> dict:
    """
    Records a payment against a specific installment -- uses the
    installment's own planned amount if amount is None, or a
    different amount if the customer paid more or less. Automatically
    rebalances the remaining schedule to match.
    """
    payload = {"method": method}
    if amount is not None:
        payload["amount"] = amount
    return _authed_post(f"/payment_plans/installments/{installment_id}/pay", payload)


def extend_installment_date(installment_id: int, new_due_date: str) -> dict:
    """Pushes back a specific installment's due date, recalculating every later installment's date from it."""
    return _authed_put(f"/payment_plans/installments/{installment_id}/extend", {"new_due_date": new_due_date})


def list_device_user_accounts(device_id: int) -> list[dict]:
    """Returns every user account known for a device, with passwords decrypted for display."""
    return _authed_get(f"/device_user_accounts/?device_id={device_id}")


def create_device_user_account(device_id: int, account_name: str, password: str | None, is_admin: bool) -> dict:
    """Adds a new user account to a device. Password is encrypted server-side before storage."""
    return _authed_post("/device_user_accounts/", {
        "device_id": device_id, "account_name": account_name, "password": password, "is_admin": is_admin,
    })


def update_device_user_account(account_id: int, payload: dict) -> dict:
    """Updates an existing device user account."""
    return _authed_put(f"/device_user_accounts/{account_id}", payload)


def delete_device_user_account(account_id: int):
    """Removes a user account from a device."""
    delete_lookup_item("/device_user_accounts/", account_id)


def get_business_info() -> dict:
    """Fetches the shop's full business info. Never includes the actual email password, only whether one is set. Requires superuser."""
    return _authed_get("/business_info_settings/")


def save_business_info(business_name: str, business_phone: str, email_address: str, email_password: str | None, smtp_host: str, smtp_port: int, imap_host: str, imap_port: int) -> dict:
    """Saves the shop's business info. Pass email_password=None to leave the currently-stored password unchanged. Requires superuser."""
    return _authed_put("/business_info_settings/", {
        "business_name": business_name, "business_phone": business_phone,
        "email_address": email_address, "email_password": email_password,
        "smtp_host": smtp_host, "smtp_port": smtp_port, "imap_host": imap_host, "imap_port": imap_port,
    })


def list_services() -> list[dict]:
    """Returns all billable services. Requires superuser."""
    return _authed_get("/services/")


def list_discounts() -> list[dict]:
    """Returns all discounts. Requires superuser."""
    return _authed_get("/discounts/")


def list_tax_rates() -> list[dict]:
    """Returns all tax rates. Requires superuser."""
    return _authed_get("/tax_rates/")


def list_message_templates() -> list[dict]:
    """
    Returns every reusable notes template.

    Returns:
        A list of {"id", "name", "body"} dicts.
    """
    return _authed_get("/message_templates/")


def list_background_jobs(job_type: str | None = None, status: str | None = None) -> list[dict]:
    """
    Returns background job run history, most recent first, optionally
    filtered server-side by job type and/or status.

    Args:
        job_type: If given, only jobs of this type.
        status: If given, only jobs currently in this status.

    Returns:
        A list of background job entry dicts.
    """
    params = []
    if job_type is not None:
        params.append(f"job_type={job_type}")
    if status is not None:
        params.append(f"status={status}")
    query_string = f"?{'&'.join(params)}" if params else ""
    return _authed_get(f"/background_jobs/{query_string}")


def list_audit_log_for_ticket(ticket_id: int) -> list[dict]:
    """
    Returns a single ticket's own audit trail entries (created,
    updated, an inbound email matching, an outbound notification
    sending or failing), most recent first. Filtered server-side.

    Uses the ticket-scoped endpoint, not the general /audit_logs/ one
    -- this works for any user with ticket access, not just superusers,
    since one ticket's own history is far less sensitive than browsing
    the full audit log across every user and entity.

    Args:
        ticket_id: The ticket to fetch audit history for.
    """
    return _authed_get(f"/tickets/{ticket_id}/audit-log")


def list_audit_logs(user_id: int | None = None, entity_type: str | None = None) -> list[dict]:
    """
    Returns audit trail entries, most recent first, optionally
    filtered server-side to a specific user and/or entity type.
    Requires superuser.

    Args:
        user_id: If given, only entries performed by this user.
        entity_type: If given, only entries for this kind of entity
            (e.g. "ticket", "user", "customer").

    Returns:
        A list of audit log entry dicts.
    """
    params = []
    if user_id is not None:
        params.append(f"user_id={user_id}")
    if entity_type is not None:
        params.append(f"entity_type={entity_type}")
    query_string = f"?{'&'.join(params)}" if params else ""
    return _authed_get(f"/audit_logs/{query_string}")


def list_system_settings() -> list[dict]:
    """
    Returns every configured system setting. Requires superuser.

    Returns:
        A list of {"id": ..., "key": ..., "value": ...} dicts.
    """
    return _authed_get("/system_settings/")


def save_system_setting(key: str, value: str) -> dict:
    """
    Creates or updates a system setting by its key name. Requires
    superuser.

    Args:
        key: The setting's key, e.g. "lock_timeout_minutes".
        value: The new value to store.

    Returns:
        The created or updated setting record.
    """
    return _authed_put(f"/system_settings/by-key/{key}", {"value": value})
