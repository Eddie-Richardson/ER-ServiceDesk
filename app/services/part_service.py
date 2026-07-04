# ER-ServiceDesk/app/services/part_service.py
# Service layer for Part.
"""
Business logic for Part operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

from sqlalchemy.orm import Session
from app.crud.part import crud_part
from app.schemas.part import PartCreate, PartUpdate

class PartService:
    """Business logic for Part operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Part by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Part instance, or None if not found.
        """
        return crud_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Part records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Part instances.
        """
        return crud_part.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PartCreate):
        """
        Create a new Part using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Part instance.
        """
        return crud_part.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: PartUpdate):
        """
        Update an existing Part using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Part instance.
        """
        db_obj = crud_part.get(db, id)
        return crud_part.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Part by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_part.delete(db, id)

part_service = PartService()
