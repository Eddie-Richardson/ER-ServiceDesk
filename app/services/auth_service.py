# ER-ServiceDesk/app/services/auth_service.py
# Authentication service.
#
# Handles user authentication, password verification, and token generation.
# This module sits between the API layer and the database layer, providing
# the business logic for validating credentials and issuing JWT access tokens.
# It is used by the /auth/login route to authenticate users and return tokens.

# ---------------------------------------------------------------------------
# Authentication Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.core.security import verify_password, create_access_token
from app.models.user import User


class AuthService:
    # Authenticates a user using email and password.
    def authenticate(self, db: Session, email_in: str, password: str) -> User | None:
        """
        Validate user credentials and return the matching User instance.

        Behavioral notes:
        - Queries the database for a user with the given email.
        - Verifies the provided password against the stored bcrypt hash.
        - Returns None if authentication fails.
        """
        user = db.query(User).filter(User.email == email_in).first()
        if not user or not verify_password(password, user.hashed_password):
            return None
        return user

    # Generates an access token for a user.
    def login(self, user: User):
        """
        Generate and return an access token for the authenticated user.

        Behavioral notes:
        - Delegates token creation to create_access_token.
        - Encodes the user's ID in the "sub" claim.
        """
        return {
            "access_token": create_access_token({"sub": str(user.id)}),
            "token_type": "bearer"
        }


auth_service = AuthService()
