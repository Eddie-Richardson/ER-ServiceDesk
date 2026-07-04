# ER-ServiceDesk/app/routes/messages.py
# API routes for Message operations.
"""
REST endpoints for a customer-facing message exchanged on a ticket (e.g. via email).

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.message_service import message_service
from app.schemas.message import Message, MessageCreate, MessageUpdate

router = APIRouter(prefix="/messages", tags=["messages"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[Message])
def list_messages(db: Session = Depends(get_db)):
    """
    List a customer-facing message exchanged on a ticket (e.g. via email), paginated.

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
    Create a new Message record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Message record.
    """
    return message_service.create(db, obj_in)

@router.put("/{id}", response_model=Message)
def update_message(id: int, obj_in: MessageUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Message record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Message record.
    """
    return message_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_message(id: int, db: Session = Depends(get_db)):
    """
    Delete a Message record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return message_service.delete(db, id)
