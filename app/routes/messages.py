# ER-ServiceDesk/app/routes/messages.py
# API routes for Message operations.
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
from app.services.message_service import message_service
from app.schemas.message import Message, MessageCreate, MessageUpdate

# Gated on tickets.manage, matching tickets.py's own gate -- an entry
# lives on a ticket, so viewing/creating one should require the same
# access as the ticket itself. Author-or-admin authorization for
# editing/deleting a SPECIFIC entry is a further, narrower check
# handled inside message_service itself (it depends on which entry,
# not a blanket permission).
router = APIRouter(prefix="/messages", tags=["messages"], dependencies=[Depends(require_permission("tickets.manage"))])

@router.get("/", response_model=list[Message])
def list_messages(db: Session = Depends(get_db)):
    """Visible to anyone with ticket access -- shared history, not private to its author."""
    return message_service.get_multi(db)

@router.get("/{id}", response_model=Message)
def get_message(id: int, db: Session = Depends(get_db)):
    return message_service.get(db, id)

@router.post("/", response_model=Message)
def create_message(obj_in: MessageCreate, db: Session = Depends(get_db)):
    """If direction is "outbound", this also sends the content to the customer via email -- see message_service.create() for the full behavior."""
    return message_service.create(db, obj_in)

@router.put("/{id}", response_model=Message)
def update_message(
    id: int,
    obj_in: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """See message_service.update() for who's allowed to do this."""
    return message_service.update(db, id, obj_in, current_user)

@router.delete("/{id}")
def delete_message(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """See message_service.delete() for who's allowed to do this."""
    return message_service.delete(db, id, current_user)
