# ER-ServiceDesk/app/schemas/user.py
# Pydantic schemas for User entities.
"""
Request/response schemas for User accounts.

hashed_password is intentionally never part of any schema returned to a
client. Clients send a plaintext `password` on create/update; the service
layer hashes it before it ever touches the database or a response.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class UserLogin(BaseModel):
    """Credentials submitted to the login endpoint."""
    email: str
    password: str

class UserBase(BaseModel):
    """Shared, non-sensitive fields for User across create/read/update."""
    email: str
    first_name: str
    last_name: str
    is_active: bool = True
    is_superuser: bool = False

class UserCreate(UserBase):
    """
    Schema for creating a new User record.

    No password field -- the service layer generates a random temp
    password server-side and emails it to the account's address. The
    admin never chooses or sees the real password, only that it was
    sent; the new user is forced to set their own on first login (see
    User.must_change_password / POST /auth/change-password).
    """
    pass

class UserUpdate(BaseModel):
    """
    Schema for partially updating an existing User record. All fields
    optional.

    No password field here either -- changing a password always goes
    through either the self-service change-password flow (the user
    knows their current password) or the admin Reset Password action
    (which generates and emails a new temp password), never a direct
    admin-typed value.
    """
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    updated_at: datetime | None = None

class ChangePasswordRequest(BaseModel):
    """
    Schema for the self-service password change endpoint
    (POST /auth/change-password). Re-verifies current_password the same
    way login does, rather than trusting a prior auth check -- this
    endpoint is deliberately reachable without a normal access token,
    since its whole purpose is letting someone with only a temp
    password (and therefore no token yet) set their own.
    """
    email: str
    current_password: str
    new_password: str

class User(UserBase):
    """Schema returned to the client for a User record. Excludes hashed_password."""
    id: int
    must_change_password: bool
    created_at: datetime
    updated_at: datetime
    full_name: str

    model_config = ConfigDict(from_attributes=True)
