# ER-ServiceDesk/app/schemas/permission.py
# Pydantic schemas for Permission entities used to validate and structure a single grantable capability in the RBAC system
"""
Pydantic schemas for Permission entities used to validate and structure a single grantable capability in the RBAC system.
"""

from pydantic import BaseModel
from typing import List
from app.schemas.role_permission import RolePermission

class PermissionBase(BaseModel):
    """Shared fields for Permission across create/read/update."""
    name: str
    description: str | None = None

class PermissionCreate(PermissionBase):
    """Schema for creating a new Permission record (client -> server)."""
    pass

class PermissionUpdate(BaseModel):
    """Schema for partially updating an existing Permission record. All fields optional."""
    name: str | None = None
    description: str | None = None

class Permission(PermissionBase):
    """Schema returned to the client for a Permission record (server -> client)."""
    id: int
    role_permissions: List[RolePermission] = []
    class Config:
        orm_mode = True
