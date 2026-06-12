# ER-ServiceDesk/app/crud/note.py
# CRUD operations for the Note model.
#
# Provides database access for creating, reading, updating, and deleting Note records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.note import Note
from app.schemas.note import NoteCreate, NoteUpdate

class NoteCRUD:
    # Retrieves a single Note by ID.
    def get(self, db: Session, id: int) -> Note | None:
        """
        Returns a single Note instance matching the given ID.
        """
        return db.query(Note).filter(Note.id == id).first()

    # Retrieves multiple Note records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Note records with pagination support.
        """
        return db.query(Note).offset(skip).limit(limit).all()

    # Creates a new Note record.
    def create(self, db: Session, obj_in: NoteCreate) -> Note:
        """
        Creates a new Note using the provided input schema.
        """
        obj = Note(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Note record.
    def update(self, db: Session, db_obj: Note, obj_in: NoteUpdate) -> Note:
        """
        Updates the given Note instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Note record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Note instance matching the given ID.
        """
        obj = db.query(Note).filter(Note.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_note = NoteCRUD()
