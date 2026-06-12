# ER-ServiceDesk/app/crud/role_permission.py
# CRUD operations for the RolePermission model.
#
# Provides database access for creating, reading, updating, and deleting RolePermission records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.role_permission import RolePermission
from app.schemas.role_permission import RolePermissionCreate, RolePermissionUpdate

class RolePermissionCRUD:
    # Retrieves a single RolePermission by ID.
    def get(self, db: Session, id: int) -> RolePermission | None:
        """
        Returns a single RolePermission instance matching the given ID.
        """
        return db.query(RolePermission).filter(RolePermission.id == id).first()

    # Retrieves multiple RolePermission records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of RolePermission records with pagination support.
        """
        return db.query(RolePermission).offset(skip).limit(limit).all()

    # Creates a new RolePermission record.
    def create(self, db: Session, obj_in: RolePermissionCreate) -> RolePermission:
        """
        Creates a new RolePermission using the provided input schema.
        """
        obj = RolePermission(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing RolePermission record.
    def update(self, db: Session, db_obj: RolePermission, obj_in: RolePermissionUpdate) -> RolePermission:
        """
        Updates the given RolePermission instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a RolePermission record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the RolePermission instance matching the given ID.
        """
        obj = db.query(RolePermission).filter(RolePermission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role_permission = RolePermissionCRUD()
