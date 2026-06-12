# ER-ServiceDesk/app/services/role_permission_service.py
# Service layer for RolePermission.
#
# Provides business logic for RolePermission operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.role_permission import crud_role_permission
from app.schemas.role_permission import RolePermissionCreate, RolePermissionUpdate

class RolePermissionService:
    # Retrieves a single RolePermission by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single RolePermission instance.
        """
        return crud_role_permission.get(db, id)

    # Retrieves multiple RolePermission records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of RolePermission records.
        """
        return crud_role_permission.get_multi(db, skip, limit)

    # Creates a new RolePermission.
    def create(self, db: Session, obj_in: RolePermissionCreate):
        """
        Creates a new RolePermission using validated input data.
        """
        return crud_role_permission.create(db, obj_in)

    # Updates an existing RolePermission.
    def update(self, db: Session, id: int, obj_in: RolePermissionUpdate):
        """
        Updates an existing RolePermission using validated input data.
        """
        db_obj = crud_role_permission.get(db, id)
        return crud_role_permission.update(db, db_obj, obj_in)

    # Deletes a RolePermission by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a RolePermission instance.
        """
        return crud_role_permission.delete(db, id)

role_permission_service = RolePermissionService()
