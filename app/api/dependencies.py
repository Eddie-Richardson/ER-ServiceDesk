# ER-ServiceDesk/app/api/dependencies.py
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
from app.services.permission_service import permission_service
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Resolve the currently authenticated user from a JWT bearer token.

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

    Raises:
        HTTPException: 403 if the user is authenticated but not a superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def require_permission(permission_name: str):
    """
    Dependency factory that restricts access to users holding a specific
    permission through any of their assigned roles.

    Superusers always bypass this check, before any role/permission
    lookup even happens -- is_superuser is a direct flag on the user,
    deliberately independent of the Role system, so it can never be
    lost as a side effect of a role or permission being misconfigured
    or removed.

    Args:
        permission_name: The permission required, e.g. "tickets.manage".

    Returns:
        A FastAPI dependency function suitable for use in
        `dependencies=[Depends(require_permission("..."))]`.

    Usage:
        router = APIRouter(
            ...,
            dependencies=[Depends(require_permission("tickets.manage"))],
        )
    """
    def check_permission(
        current_user: User = Depends(get_current_user),
    ) -> User:
        """
        Raises:
            HTTPException: 403 if the user is authenticated but lacks
                the required permission and isn't a superuser.
        """
        if current_user.is_superuser:
            return current_user

        user_permissions = permission_service.get_user_permission_names(current_user)
        if permission_name not in user_permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user

    return check_permission
