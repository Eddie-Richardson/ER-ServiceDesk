# ER-ServiceDesk/app/services/note_service.py
# Service layer for Note.
#
# Provides business logic for Note operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.note import crud_note
from app.schemas.note import NoteCreate, NoteUpdate

class NoteService:
    # Retrieves a single Note by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Note instance.
        """
        return crud_note.get(db, id)

    # Retrieves multiple Note records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Note records.
        """
        return crud_note.get_multi(db, skip, limit)

    # Creates a new Note.
    def create(self, db: Session, obj_in: NoteCreate):
        """
        Creates a new Note using validated input data.
        """
        return crud_note.create(db, obj_in)

    # Updates an existing Note.
    def update(self, db: Session, id: int, obj_in: NoteUpdate):
        """
        Updates an existing Note using validated input data.
        """
        db_obj = crud_note.get(db, id)
        return crud_note.update(db, db_obj, obj_in)

    # Deletes a Note by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Note instance.
        """
        return crud_note.delete(db, id)

note_service = NoteService()
