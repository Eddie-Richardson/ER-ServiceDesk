# ER-ServiceDesk/app/services/permission_service.py
# Service layer for Permission.
#
# Provides business logic for Permission operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.permission import crud_permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionService:
    # Retrieves a single Permission by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Permission instance.
        """
        return crud_permission.get(db, id)

    # Retrieves multiple Permission records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Permission records.
        """
        return crud_permission.get_multi(db, skip, limit)

    # Creates a new Permission.
    def create(self, db: Session, obj_in: PermissionCreate):
        """
        Creates a new Permission using validated input data.
        """
        return crud_permission.create(db, obj_in)

    # Updates an existing Permission.
    def update(self, db: Session, id: int, obj_in: PermissionUpdate):
        """
        Updates an existing Permission using validated input data.
        """
        db_obj = crud_permission.get(db, id)
        return crud_permission.update(db, db_obj, obj_in)

    # Deletes a Permission by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Permission instance.
        """
        return crud_permission.delete(db, id)

permission_service = PermissionService()
