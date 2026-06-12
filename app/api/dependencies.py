# ER-ServiceDesk/app/api/dependencies.py
# Authentication and user dependencies
#
# This module defines FastAPI dependency functions used to enforce authentication
# and retrieve the current user from JWT tokens.
# It connects the security layer (JWT handling) with the user service and model,
# providing reusable building blocks for protected routes.
# It is used throughout the API layer wherever authenticated access is required.

# ---------------------------------------------------------------------------
# Authentication dependencies
# ---------------------------------------------------------------------------

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.security import create_access_token, verify_password  # if used elsewhere
from app.core.security import decode_access_token  # if you add it later
from app.services.user_service import get_user_by_id
from app.models.user import User

# oauth2_scheme: Defines how the application expects clients to provide tokens.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    Retrieve the current authenticated user from a JWT access token.

    Decodes the provided token, extracts the user identifier, and loads the
    corresponding user from the data store.

    Raises HTTPException(401) if the token is invalid or the user cannot be found.
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
        )

    user = get_user_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user
