# ER-ServiceDesk/app/crud/role.py
# CRUD operations for the Role model.
"""
Database access layer for an authorization grouping assigned to users.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.role import Role
from app.schemas.role import RoleCreate, RoleUpdate

class RoleCRUD:
    """Direct database access for Role records."""

    def get(self, db: Session, id: int) -> Role | None:
        """
        Fetch a single Role by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Role instance, or None if no record exists.
        """
        return db.query(Role).filter(Role.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Role records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Role instances.
        """
        return db.query(Role).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: RoleCreate) -> Role:
        """
        Insert a new Role record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Role instance.
        """
        obj = Role(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Role, obj_in: RoleUpdate) -> Role:
        """
        Apply a partial update to an existing Role record.

        Args:
            db: Active database session.
            db_obj: The existing Role instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Role instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Role record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Role).filter(Role.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_role = RoleCRUD()
