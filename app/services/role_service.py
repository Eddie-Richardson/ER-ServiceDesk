# ER-ServiceDesk/app/services/role_service.py
# Service layer for Role.
"""
Business logic for an authorization grouping assigned to users.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.role import crud_role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleService:
    """Business logic for Role operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Role by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Role instance, or None if not found.
        """
        return crud_role.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Role records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Role instances.
        """
        return crud_role.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: RoleCreate):
        """
        Create a new Role using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Role instance.
        """
        return crud_role.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: RoleUpdate):
        """
        Update an existing Role using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Role instance.
        """
        db_obj = crud_role.get(db, id)
        return crud_role.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Role by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_role.delete(db, id)

role_service = RoleService()
