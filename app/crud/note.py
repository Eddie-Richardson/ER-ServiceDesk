# ER-ServiceDesk/app/crud/note.py
# CRUD operations for the Note model.
"""
Database access layer for an internal or customer-visible annotation on a ticket.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate

class NoteCRUD:
    """Direct database access for Note records."""

    def get(self, db: Session, id: int) -> Note | None:
        """
        Fetch a single Note by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Note instance, or None if no record exists.
        """
        return db.query(Note).filter(Note.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Note records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Note instances.
        """
        return db.query(Note).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: NoteCreate) -> Note:
        """
        Insert a new Note record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Note instance.
        """
        obj = Note(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Note, obj_in: NoteUpdate) -> Note:
        """
        Apply a partial update to an existing Note record.

        Args:
            db: Active database session.
            db_obj: The existing Note instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Note instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Note record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Note).filter(Note.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_note = NoteCRUD()
