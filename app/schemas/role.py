# ER-ServiceDesk/app/schemas/role.py
# Pydantic schemas for Role entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning role records within the ER‑ServiceDesk RBAC system.
# Roles represent authorization groupings and are linked to users
# through the UserRole association table. Roles are also linked to
# permissions through the RolePermission association table.

from pydantic import BaseModel
from typing import List

from app.schemas.role_permission import RolePermission

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class RoleBase(BaseModel):
    name: str
    description: str | None = None

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class RoleCreate(RoleBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class RoleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Role(RoleBase):
    id: int
    role_permissions: List[RolePermission] = []

    class Config:
        orm_mode = True
