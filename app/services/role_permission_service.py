# ER-ServiceDesk/app/services/role_permission_service.py
# Service layer for RolePermission.
"""
Business logic for the many-to-many link between roles and permissions.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.role_permission import crud_role_permission
from app.schemas.role_permission import RolePermissionCreate, RolePermissionUpdate

class RolePermissionService:
    """Business logic for RolePermission operations."""

    def get(self, db: Session, id: int):
        return crud_role_permission.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_role_permission.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: RolePermissionCreate):
        return crud_role_permission.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: RolePermissionUpdate):
        db_obj = crud_role_permission.get(db, id)
        return crud_role_permission.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_role_permission.delete(db, id)

role_permission_service = RolePermissionService()
