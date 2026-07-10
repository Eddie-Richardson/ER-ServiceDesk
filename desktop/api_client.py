# ER-ServiceDesk/desktop/api_client.py
# Thin API client for talking to the FastAPI backend.
#
# Kept deliberately small: right now it only knows how to log in. As more
# windows need the API (Tickets, Inventory, etc.) they can add their own
# request functions here, all sharing BASE_URL and the same error-handling
# shape established by login().

import requests

BASE_URL = "http://localhost:8000"


class LoginError(Exception):
    """
    Raised when login fails for a reason the person can act on --
    wrong credentials, or the backend being unreachable. The message is
    written to be shown directly in the UI.
    """
    pass


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
