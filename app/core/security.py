# ER-ServiceDesk/app/core/security.py
# Password hashing and verification utilities

from passlib.context import CryptContext

# Configure Passlib to use bcrypt for hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    # Hash a plaintext password
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    # Verify a plaintext password against a stored hash
    return pwd_context.verify(plain, hashed)
