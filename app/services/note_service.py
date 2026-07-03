# ER-ServiceDesk/app/services/note_service.py
# Service layer for Note.
"""
Business logic for an internal or customer-visible annotation on a ticket.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.note import crud_note
from app.schemas.note import NoteCreate, NoteUpdate

class NoteService:
    """Business logic for Note operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Note by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Note instance, or None if not found.
        """
        return crud_note.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Note records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Note instances.
        """
        return crud_note.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: NoteCreate):
        """
        Create a new Note using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Note instance.
        """
        return crud_note.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: NoteUpdate):
        """
        Update an existing Note using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Note instance.
        """
        db_obj = crud_note.get(db, id)
        return crud_note.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Note by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_note.delete(db, id)

note_service = NoteService()
