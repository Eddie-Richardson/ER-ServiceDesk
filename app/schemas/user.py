# ER-ServiceDesk/app/schemas/user.py
# Pydantic schemas for User entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning user records within the ER‑ServiceDesk platform.
# Users represent authenticated system accounts with roles, profile
# information, and status flags used throughout authorization and
# account‑management workflows.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class UserBase(BaseModel):
    email: str
    hashed_password: str
    first_name: str
    last_name: str
    is_active: bool
    is_superuser: bool

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class UserCreate(UserBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class UserUpdate(BaseModel):
    email: str | None = None
    hashed_password: str | None = None
    first_name: str | None = None
    last_name: str  | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class User(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime
    full_name: str

    class Config:
        orm_mode = True