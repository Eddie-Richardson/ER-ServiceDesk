# ER-ServiceDesk/app/routes/messages.py
# API routes for Message operations.
#
# Exposes REST endpoints for interacting with Message records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.message_service import message_service
from app.schemas.message import Message, MessageCreate, MessageUpdate

router = APIRouter(prefix="/messages", tags=["messages"])

@router.get("/", response_model=list[Message])
def list_messages(db: Session = Depends(get_db)):
    """
    Returns a list of Message records.
    """
    return message_service.get_multi(db)

@router.get("/{id}", response_model=Message)
def get_message(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Message record by ID.
    """
    return message_service.get(db, id)

@router.post("/", response_model=Message)
def create_message(obj_in: MessageCreate, db: Session = Depends(get_db)):
    """
    Creates a new Message record.
    """
    return message_service.create(db, obj_in)

@router.put("/{id}", response_model=Message)
def update_message(id: int, obj_in: MessageUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Message record.
    """
    return message_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_message(id: int, db: Session = Depends(get_db)):
    """
    Deletes a Message record by ID.
    """
    return message_service.delete(db, id)
