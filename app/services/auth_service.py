# ER-ServiceDesk/app/services/auth_service.py
# Authentication service.
"""
Business logic for authenticating users and issuing access tokens.
Sits between the /auth/login route and the User model.
"""

from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.services.permission_service import permission_service


class AuthService:
    """Handles credential verification and token issuance."""

    def authenticate(self, db: Session, email_in: str, password: str) -> User | None:
        """
        Validate a user's credentials.

        Args:
            db: Active database session.
            email_in: The email submitted at login.
            password: The plaintext password submitted at login.

        Returns:
            The matching User if credentials are valid, otherwise None.
        """
        user = db.query(User).filter(User.email == email_in).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    def login(self, user: User):
        """
        Issue an access token for an already-authenticated user.

        Args:
            user: The authenticated User instance.

        Returns:
            A dict containing the access token and token type.

        Note:
            The token carries is_superuser, the user's effective
            permissions (computed from their assigned roles), and
            email/full_name for display purposes, so clients can
            determine access and identity without a separate API call.
            This means a role or permission change won't take effect
            for an already-issued token until the user logs in again --
            acceptable for this system's scale, but worth knowing.
        """
        permissions = sorted(permission_service.get_user_permission_names(user))
        return {
            "access_token": create_access_token({
                "sub": str(user.id),
                "is_superuser": user.is_superuser,
                "permissions": permissions,
                "email": user.email,
                "full_name": user.full_name,
            }),
            "token_type": "bearer"
        }


auth_service = AuthService()
