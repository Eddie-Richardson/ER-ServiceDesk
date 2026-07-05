# ER-ServiceDesk/app/crud/permission.py
# CRUD operations for the Permission model.
"""
Database access layer for a single grantable capability in the RBAC system.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.permission import Permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionCRUD:
    """Direct database access for Permission records."""

    def get(self, db: Session, id: int) -> Permission | None:
        """
        Fetch a single Permission by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Permission instance, or None if no record exists.
        """
        return db.query(Permission).filter(Permission.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Permission records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Permission instances.
        """
        return db.query(Permission).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: PermissionCreate) -> Permission:
        """
        Insert a new Permission record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Permission instance.
        """
        obj = Permission(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Permission, obj_in: PermissionUpdate) -> Permission:
        """
        Apply a partial update to an existing Permission record.

        Args:
            db: Active database session.
            db_obj: The existing Permission instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Permission instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Permission record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Permission).filter(Permission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_permission = PermissionCRUD()
