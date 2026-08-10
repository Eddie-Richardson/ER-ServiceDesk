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
import secrets
import string
from app.core.config import settings

pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

# Excludes visually ambiguous characters (0/O, 1/l/I) and characters that
# occasionally cause friction if a password needs to be typed manually
# despite being emailed for copy/paste (quotes, backslash).
_TEMP_PASSWORD_ALPHABET = "".join(
    c for c in (string.ascii_letters + string.digits + "!@#$%^&*")
    if c not in "0O1lI\"'\\"
)


def generate_temp_password(length: int = 12) -> str:
    """
    Generates a cryptographically random temporary password, used when
    an admin creates a new account or resets an existing one -- the
    admin never chooses or sees a real password, only this generated
    one, which the user is forced to change on first login.

    Args:
        length: How many characters to generate. 12 comfortably clears
            any reasonable minimum while staying well under bcrypt's
            72-byte hashing limit.

    Returns:
        A random password string, safe to include in an email body.
    """
    return "".join(secrets.choice(_TEMP_PASSWORD_ALPHABET) for _ in range(length))


MIN_PASSWORD_LENGTH = 8
# bcrypt silently ignores/errors on anything past 72 bytes -- this is a
# hard algorithm limit, not a tunable setting. Enforced here so an
# over-length password gets a clean message instead of a raw exception
# from deep inside passlib.
MAX_PASSWORD_LENGTH_BYTES = 72


def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    Args:
        password: The raw password to hash.

    Returns:
        A salted bcrypt hash suitable for storage.

    Raises:
        ValueError: If the password is shorter than MIN_PASSWORD_LENGTH,
            its UTF-8 byte length exceeds bcrypt's MAX_PASSWORD_LENGTH_BYTES
            limit, or it's missing a required character variety (upper,
            lower, digit, special) -- all checked here, before bcrypt
            itself would raise a less helpful error, and enforced
            centrally since every user-chosen password change (not
            system-generated temp passwords, which already have variety
            by construction) routes through this one function.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password.encode("utf-8")) > MAX_PASSWORD_LENGTH_BYTES:
        raise ValueError(f"Password must be under {MAX_PASSWORD_LENGTH_BYTES} bytes.")
    if not any(c.isupper() for c in password):
        raise ValueError("Password must include at least one uppercase letter.")
    if not any(c.islower() for c in password):
        raise ValueError("Password must include at least one lowercase letter.")
    if not any(c.isdigit() for c in password):
        raise ValueError("Password must include at least one number.")
    if not any(not c.isalnum() for c in password):
        raise ValueError("Password must include at least one special character.")
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
