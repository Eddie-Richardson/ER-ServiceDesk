# ER-ServiceDesk/app/services/user_role_service.py
# Service layer for UserRole.
"""
Business logic for the many-to-many link between users and roles.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.user_role import crud_user_role
from app.schemas.user_role import UserRoleCreate, UserRoleUpdate

class UserRoleService:
    """Business logic for UserRole operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single UserRole by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching UserRole instance, or None if not found.
        """
        return crud_user_role.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of UserRole records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of UserRole instances.
        """
        return crud_user_role.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: UserRoleCreate):
        """
        Create a new UserRole using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created UserRole instance.
        """
        return crud_user_role.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: UserRoleUpdate):
        """
        Update an existing UserRole using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated UserRole instance.
        """
        db_obj = crud_user_role.get(db, id)
        return crud_user_role.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a UserRole by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_user_role.delete(db, id)

user_role_service = UserRoleService()
