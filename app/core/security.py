# ER-ServiceDesk/app/core/security.py
# Password hashing, verification, and access token utilities
"""
Cryptographic primitives for authentication: password hashing/verification
and JWT access token creation/decoding. Used by the auth service and any
route that needs to authenticate a request.
"""

from passlib.context import CryptContext
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError
from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The raw password to hash.

    Returns:
        A salted bcrypt hash suitable for storage.
    """
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain: The password submitted at login.
        hashed: The stored bcrypt hash to compare against.

    Returns:
        True if the password matches, False otherwise.
    """
    return pwd_context.verify(plain, hashed)

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.

    Args:
        data: Claims to encode (e.g. {"sub": user_id}).
        expires_delta: Optional custom expiry; defaults to
            ACCESS_TOKEN_EXPIRE_MINUTES from settings.

    Returns:
        The encoded JWT string.
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Args:
        token: The encoded JWT string from the Authorization header.

    Returns:
        The decoded claims dict.

    Raises:
        ValueError: If the token is invalid, malformed, or expired.
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise ValueError("Invalid or expired token")
