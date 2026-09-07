# ER-ServiceDesk/app/routes/notes.py
"""
REST endpoints for a ticket's full note/conversation history --
internal notes and customer-facing email exchange, unified.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user, require_permission
from app.models.user import User
from app.services.note_service import note_service
from app.schemas.note import Note, NoteCreate, NoteUpdate

# Gated on tickets.manage, matching tickets.py's own gate -- an entry
# lives on a ticket, so viewing/creating one should require the same
# access as the ticket itself. Author-or-admin authorization for
# editing/deleting a SPECIFIC entry is a further, narrower check
# handled inside note_service itself (it depends on which entry,
# not a blanket permission).
router = APIRouter(prefix="/notes", tags=["notes"], dependencies=[Depends(require_permission("tickets.manage"))])

@router.get("/", response_model=list[Note])
def list_notes(ticket_id: int | None = None, db: Session = Depends(get_db)):
    """
    Visible to anyone with ticket access -- shared history, not
    private to its author. Optionally filtered to one ticket via
    ticket_id -- the desktop client always passes it (see
    api_client.list_notes_for_ticket()), filtering server-side
    rather than fetching everything and filtering client-side, since
    the unfiltered list's own limit is a system-wide cap, not a
    per-ticket one, and could otherwise silently truncate an older
    ticket's real conversation history once enough other notes
    accumulate elsewhere in the system.
    """
    return note_service.get_multi(db, ticket_id=ticket_id)

@router.get("/{id}", response_model=Note)
def get_note(id: int, db: Session = Depends(get_db)):
    return note_service.get(db, id)

@router.post("/", response_model=Note)
def create_note(obj_in: NoteCreate, db: Session = Depends(get_db)):
    """If direction is "outbound", this also sends the content to the customer via email -- see note_service.create() for the full behavior."""
    return note_service.create(db, obj_in)

@router.put("/{id}", response_model=Note)
def update_note(
    id: int,
    obj_in: NoteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """See note_service.update() for who's allowed to do this."""
    return note_service.update(db, id, obj_in, current_user)

@router.delete("/{id}")
def delete_note(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """See note_service.delete() for who's allowed to do this."""
    return note_service.delete(db, id, current_user)
