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
    Takes a plaintext password; the service layer hashes it before storage.
    """
    password: str

class UserUpdate(BaseModel):
    """Schema for partially updating an existing User record. All fields optional."""
    email: str | None = None
    password: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    updated_at: datetime | None = None

class User(UserBase):
    """Schema returned to the client for a User record. Excludes hashed_password."""
    id: int
    created_at: datetime
    updated_at: datetime
    full_name: str

    model_config = ConfigDict(from_attributes=True)
