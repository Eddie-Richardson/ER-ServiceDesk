# ER-ServiceDesk/app/api/dependencies.py
# Authentication and user dependencies
"""
FastAPI dependencies for authenticating requests and enforcing access
control. Import these into any route that should require a logged-in
user (or, via require_superuser, an admin).
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.services.user_service import user_service
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a JWT bearer token.

    Args:
        token: The JWT extracted from the Authorization header.
        db: Injected database session.

    Returns:
        The authenticated User instance.

    Raises:
        HTTPException: 401 if the token is invalid, expired, or does not
            correspond to an existing user.
    """
    try:
        payload = decode_access_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise ValueError("Token missing subject claim")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = user_service.get(db, int(user_id))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_superuser(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency that restricts access to superuser accounts only.

    Use for admin-only endpoints (e.g. user/role management).

    Args:
        current_user: The already-authenticated user (via get_current_user).

    Returns:
        The same User instance, if they are a superuser.

    Raises:
        HTTPException: 403 if the user is authenticated but not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user
