# ER-ServiceDesk/app/services/permission_service.py
# Service layer for Permission.
"""
Business logic for a single grantable capability in the RBAC system.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.permission import crud_permission
from app.schemas.permission import PermissionCreate, PermissionUpdate

class PermissionService:
    """Business logic for Permission operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Permission by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Permission instance, or None if not found.
        """
        return crud_permission.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Permission records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Permission instances.
        """
        return crud_permission.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PermissionCreate):
        """
        Create a new Permission using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Permission instance.
        """
        return crud_permission.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: PermissionUpdate):
        """
        Update an existing Permission using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Permission instance.
        """
        db_obj = crud_permission.get(db, id)
        return crud_permission.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Permission by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_permission.delete(db, id)

permission_service = PermissionService()
