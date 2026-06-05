# ER-ServiceDesk/app/schemas/permission.py
# Pydantic schemas for Permission entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning permission records within the ER‑ServiceDesk system.
# Permissions represent individual access capabilities used by the
# RBAC authorization layer and are typically assigned to roles.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class PermissionBase(BaseModel):
    name: str
    description: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class PermissionCreate(PermissionBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class PermissionUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Permission(PermissionBase):
    id: int

    class Config:
        orm_mode = True

