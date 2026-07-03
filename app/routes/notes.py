# ER-ServiceDesk/app/routes/notes.py
# API routes for Note operations.
"""
REST endpoints for an internal or customer-visible annotation on a ticket.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.note_service import note_service
from app.schemas.note import Note, NoteCreate, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/", response_model=list[Note])
def list_notes(db: Session = Depends(get_db)):
    """
    List an internal or customer-visible annotation on a ticket, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Note records.
    """
    return note_service.get_multi(db)

@router.get("/{id}", response_model=Note)
def get_note(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Note record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Note record.
    """
    return note_service.get(db, id)

@router.post("/", response_model=Note)
def create_note(obj_in: NoteCreate, db: Session = Depends(get_db)):
    """
    Create a new Note record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Note record.
    """
    return note_service.create(db, obj_in)

@router.put("/{id}", response_model=Note)
def update_note(id: int, obj_in: NoteUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Note record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Note record.
    """
    return note_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_note(id: int, db: Session = Depends(get_db)):
    """
    Delete a Note record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return note_service.delete(db, id)
