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

BASE_URL = "http://localhost:8000"


class LoginError(Exception):
    """
    Raised when login fails for a reason the person can act on --
    wrong credentials, or the backend being unreachable. The message is
    written to be shown directly in the UI.
    """
    pass


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
            detail = response.json().get("detail", "")
        except ValueError:
            pass
        raise ApiError(detail or f"Request failed (server returned {response.status_code}).")

    return response.json()


def list_tickets() -> list[dict]:
    """Returns all tickets. Requires an active session."""
    return _authed_get("/tickets/")


def list_ticket_statuses() -> list[dict]:
    """Returns all ticket statuses (id, name, color). Requires an active session."""
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
    token = data.get("access_token")
    if not token:
        raise LoginError("Login succeeded but no access token was returned.")

    return token
