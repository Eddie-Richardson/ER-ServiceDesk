# ER-ServiceDesk/app/schemas/role_permission.py
# Pydantic schemas for RolePermission entities
"""
Request/response schemas for the many-to-many link between roles and
permissions.
"""

from pydantic import BaseModel, ConfigDict

class RolePermissionBase(BaseModel):
    """Shared fields for RolePermission across create/read/update."""
    role_id: int
    permission_id: int

class RolePermissionCreate(RolePermissionBase):
    """Schema for creating a new RolePermission record (client -> server)."""
    pass

class RolePermissionUpdate(BaseModel):
    """Schema for partially updating an existing RolePermission record. All fields optional."""
    role_id: int | None = None
    permission_id: int | None = None

class RolePermission(RolePermissionBase):
    """Schema returned to the client for a RolePermission record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
