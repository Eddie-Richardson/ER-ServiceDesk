# ER-ServiceDesk/app/core/security.py
# Password hashing and verification utilities
#
# This module provides secure password hashing and verification functions
# for the ER‑ServiceDesk application. It uses Passlib's CryptContext
# configured with bcrypt, ensuring industry‑standard password security.
# These helpers are used throughout the authentication system to safely
# store and validate user credentials.

from passlib.context import CryptContext

# ---------------------------------------------------------------------------
# Passlib CryptContext configuration
# ---------------------------------------------------------------------------
# CryptContext manages hashing algorithms and settings.
# Here we configure it to use bcrypt, the recommended secure hashing scheme.
pwd_context = CryptContext(
    schemes=["bcrypt"],   # Hashing algorithm(s) to use
    deprecated="auto"     # Automatically mark older schemes as deprecated
)


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------
def hash_password(password: str) -> str:
    """
    Hash a plaintext password using bcrypt.

    This function takes a raw user password and returns a secure hash
    suitable for storage in the database. The hashing algorithm includes
    salting and multiple rounds to protect against brute‑force attacks.
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
