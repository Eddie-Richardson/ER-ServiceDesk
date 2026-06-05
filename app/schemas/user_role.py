# ER-ServiceDesk/app/schemas/user_role.py
# Pydantic schemas for UserRole entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning user‑role association records within the ER‑ServiceDesk
# RBAC system. UserRole entries represent the many‑to‑many relationship
# between users and roles, forming the foundation of permission and
# authorization logic throughout the platform.

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class UserRoleBase(BaseModel):
    user_id: int
    role_id: int

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class UserRoleCreate(UserRoleBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class UserRoleUpdate(BaseModel):
    user_id: int | None = None
    role_id: int | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class UserRole(UserRoleBase):
    id: int

    class Config:
        orm_mode = True