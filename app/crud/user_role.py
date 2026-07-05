# ER-ServiceDesk/app/crud/user_role.py
# CRUD operations for the UserRole model.
"""
Database access layer for the many-to-many link between users and roles.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.user_role import UserRole
from app.schemas.user_role import UserRoleCreate, UserRoleUpdate

class UserRoleCRUD:
    """Direct database access for UserRole records."""

    def get(self, db: Session, id: int) -> UserRole | None:
        """
        Fetch a single UserRole by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching UserRole instance, or None if no record exists.
        """
        return db.query(UserRole).filter(UserRole.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple UserRole records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of UserRole instances.
        """
        return db.query(UserRole).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: UserRoleCreate) -> UserRole:
        """
        Insert a new UserRole record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed UserRole instance.
        """
        obj = UserRole(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: UserRole, obj_in: UserRoleUpdate) -> UserRole:
        """
        Apply a partial update to an existing UserRole record.

        Args:
            db: Active database session.
            db_obj: The existing UserRole instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed UserRole instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a UserRole record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(UserRole).filter(UserRole.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_user_role = UserRoleCRUD()
