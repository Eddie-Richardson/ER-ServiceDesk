# ER-ServiceDesk/app/crud/permission.py
# CRUD operations for the Permission model.
#
# Provides database access for creating, reading, updating, and deleting Permission records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionCRUD:
    # Retrieves a single Permission by ID.
    def get(self, db: Session, id: int) -> Permission | None:
        """
        Returns a single Permission instance matching the given ID.
        """
        return db.query(Permission).filter(Permission.id == id).first()

    # Retrieves multiple Permission records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Permission records with pagination support.
        """
        return db.query(Permission).offset(skip).limit(limit).all()

    # Creates a new Permission record.
    def create(self, db: Session, obj_in: PermissionCreate) -> Permission:
        """
        Creates a new Permission using the provided input schema.
        """
        obj = Permission(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Permission record.
    def update(self, db: Session, db_obj: Permission, obj_in: PermissionUpdate) -> Permission:
        """
        Updates the given Permission instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Permission record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Permission instance matching the given ID.
        """
        obj = db.query(Permission).filter(Permission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_permission = PermissionCRUD()
