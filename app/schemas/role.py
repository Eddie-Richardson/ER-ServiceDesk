# ER-ServiceDesk/app/schemas/role.py
# Pydantic schemas for Role entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning role records within the ER‑ServiceDesk RBAC system.
# Roles represent authorization groupings and are linked to users
# through the UserRole association table.

from pydantic import BaseModel

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

    class Config:
        orm_mode = True
