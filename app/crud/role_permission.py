# ER-ServiceDesk/app/crud/role_permission.py
# CRUD operations for the RolePermission model.
"""
Database access layer for the many-to-many link between roles and permissions.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.role_permission import RolePermission
from app.schemas.role_permission import RolePermissionCreate, RolePermissionUpdate

class RolePermissionCRUD:
    """Direct database access for RolePermission records."""

    def get(self, db: Session, id: int) -> RolePermission | None:
        """
        Fetch a single RolePermission by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching RolePermission instance, or None if no record exists.
        """
        return db.query(RolePermission).filter(RolePermission.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple RolePermission records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of RolePermission instances.
        """
        return db.query(RolePermission).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: RolePermissionCreate) -> RolePermission:
        """
        Insert a new RolePermission record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed RolePermission instance.
        """
        obj = RolePermission(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: RolePermission, obj_in: RolePermissionUpdate) -> RolePermission:
        """
        Apply a partial update to an existing RolePermission record.

        Args:
            db: Active database session.
            db_obj: The existing RolePermission instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed RolePermission instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a RolePermission record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(RolePermission).filter(RolePermission.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role_permission = RolePermissionCRUD()
