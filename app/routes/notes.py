# ER-ServiceDesk/app/routes/notes.py
# API routes for Note operations.
#
# Exposes REST endpoints for interacting with Note records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.note_service import note_service
from app.schemas.note import Note, NoteCreate, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])

@router.get("/", response_model=list[Note])
def list_notes(db: Session = Depends(get_db)):
    """
    Returns a list of Note records.
    """
    return note_service.get_multi(db)

@router.get("/{id}", response_model=Note)
def get_note(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Note record by ID.
    """
    return note_service.get(db, id)

@router.post("/", response_model=Note)
def create_note(obj_in: NoteCreate, db: Session = Depends(get_db)):
    """
    Creates a new Note record.
    """
    return note_service.create(db, obj_in)

@router.put("/{id}", response_model=Note)
def update_note(id: int, obj_in: NoteUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Note record.
    """
    return note_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_note(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Note record by ID.
    """
    return note_service.delete(db, id)
