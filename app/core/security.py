# ER-ServiceDesk/app/core/security.py
# Password hashing, verification, and access token utilities
#
# This module provides secure password hashing, password verification, and
# JWT access token creation for the ER‑ServiceDesk application.
# It fits into the authentication layer of the system, supplying core
# cryptographic operations used by login, user creation, and token issuance.
# These functions are used by the authentication service and API routes
# that require secure credential handling and token generation.

# ---------------------------------------------------------------------------
# Passlib CryptContext configuration
# ---------------------------------------------------------------------------

from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import jwt
from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    This function takes a raw user password and returns a secure hash suitable
    for storage in the database. The hashing algorithm includes salting and
    multiple rounds to protect against brute‑force attacks.
    """
    return pwd_context.hash(password)

# ---------------------------------------------------------------------------
# Password verification
# ---------------------------------------------------------------------------

def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Returns True if the provided plaintext password matches the stored hash,
    otherwise returns False. Used during login to authenticate users.
    """
    return pwd_context.verify(plain, hashed)

# ---------------------------------------------------------------------------
# Access token creation
# ---------------------------------------------------------------------------
# SECRET_KEY, ALGORITHM, and ACCESS_TOKEN_EXPIRE_MINUTES are now loaded from
# environment‑backed settings instead of being hard‑coded.

SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """
    Create a signed JWT access token.

    This function takes a payload dictionary and returns a JWT string containing
    the encoded data and expiration timestamp. The token is signed using the
    configured SECRET_KEY and ALGORITHM.
    """
    to_encode = data.copy()

    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})

    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
