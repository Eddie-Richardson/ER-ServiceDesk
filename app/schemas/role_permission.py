# ER-ServiceDesk/app/schemas/role_permissions.py
# Pydantic schemas for RolePermission entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning role‑permission mapping records within the ER‑ServiceDesk
# RBAC system. RolePermission represents the association between roles
# and permissions in the authorization layer.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class RolePermissionBase(BaseModel):
    role_id: int
    permission_id: int

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class RolePermissionCreate(RolePermissionBase):
    pass

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class RolePermission(RolePermissionBase):
    id: int

    class Config:
        orm_mode = True
