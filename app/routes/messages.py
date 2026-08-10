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
    """
    List a ticket's note/conversation history, paginated. Visible to
    anyone with ticket access -- shared history, not private to its
    author.

    Args:
        db: Injected database session.

    Returns:
        A list of Message records.
    """
    return message_service.get_multi(db)

@router.get("/{id}", response_model=Message)
def get_message(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Message record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Message record.
    """
    return message_service.get(db, id)

@router.post("/", response_model=Message)
def create_message(obj_in: MessageCreate, db: Session = Depends(get_db)):
    """
    Create a new Message record. If direction is "outbound", this also
    sends the content to the customer via email -- see
    message_service.create() for the full behavior.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Message record.
    """
    return message_service.create(db, obj_in)

@router.put("/{id}", response_model=Message)
def update_message(
    id: int,
    obj_in: MessageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Edit an existing Message's content. See message_service.update()
    for who's allowed to do this.

    Args:
        id: Primary key of the record to update.
        obj_in: The new content.
        db: Injected database session.
        current_user: The authenticated user making this request.

    Returns:
        The updated Message record.
    """
    return message_service.update(db, id, obj_in, current_user)

@router.delete("/{id}")
def delete_message(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a Message record by ID. See message_service.delete() for
    who's allowed to do this.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
        current_user: The authenticated user making this request.
    """
    return message_service.delete(db, id, current_user)
