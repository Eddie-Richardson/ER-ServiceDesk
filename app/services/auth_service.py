# ER-ServiceDesk/app/services/auth_service.py
"""
Business logic for authenticating users and issuing access tokens.
Sits between the /auth/login route and the User model.
"""

from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.services.permission_service import permission_service
from app.services.audit_log_service import audit_log_service


class AuthService:
    """Handles credential verification and token issuance."""

    def authenticate(self, db: Session, email_in: str, password: str) -> User | None:
        """
        Logs a failed attempt to the audit trail if the email matches
        a real account but the password is wrong -- valuable security
        signal (a failed attempt against a specific known account). A
        genuinely unknown email isn't logged at all, since there's no
        valid entity to log it against and this is meaningfully less
        actionable than a targeted attempt against a real account.
        """
        user = db.query(User).filter(User.email == email_in).first()
        if not user or not verify_password(password, user.hashed_password):
            if user:
                audit_log_service.log(
                    db, "login_failed", "user", user.id, user_id=user.id,
                    details="Incorrect password",
                )
            return None
        return user

    def login(self, db: Session, user: User):
        """
        Issue an access token for an already-authenticated user, and
        record a successful login in the audit trail.

        Note:
            The token carries is_superuser, the user's effective
            permissions (computed from their assigned roles), and
            email/full_name for display purposes -- but these are
            read-only, UI-convenience claims, never trusted for real
            enforcement. require_permission() (see
            app.api.dependencies) always re-checks live against the
            database on every request, so a role or permission change
            takes effect on the very next request, not after
            re-login. Only the desktop app's own cached copy of these
            claims, used for local UI decisions like showing/hiding a
            button, can go stale until the user logs in again -- that's
            a UI staleness issue, not a security one.
        """
        audit_log_service.log(db, "login_success", "user", user.id, user_id=user.id)
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

    def heartbeat(self, user: User):
        """
        Issue a freshly-renewed access token for an already-verified,
        currently-active session -- called on genuine user activity to
        keep a session alive without requiring a full re-login every
        ACCESS_TOKEN_EXPIRE_MINUTES. Deliberately doesn't log to the
        audit trail the way login() does -- this fires repeatedly
        throughout a normal work session, and logging each one would
        flood the audit log with entries that aren't real login events.
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
