# ER-ServiceDesk/app/routes/message_templates.py
# API routes for MessageTemplate operations.
"""
REST endpoints for a reusable template for outbound emails/notifications.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.message_template_service import message_template_service
from app.schemas.message_template import MessageTemplate, MessageTemplateCreate, MessageTemplateUpdate

router = APIRouter(prefix="/message_templates", tags=["message_templates"])

@router.get("/", response_model=list[MessageTemplate])
def list_message_templates(db: Session = Depends(get_db)):
    """
    List a reusable template for outbound emails/notifications, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of MessageTemplate records.
    """
    return message_template_service.get_multi(db)

@router.get("/{id}", response_model=MessageTemplate)
def get_message_template(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single MessageTemplate record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching MessageTemplate record.
    """
    return message_template_service.get(db, id)

@router.post("/", response_model=MessageTemplate)
def create_message_template(obj_in: MessageTemplateCreate, db: Session = Depends(get_db)):
    """
    Create a new MessageTemplate record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created MessageTemplate record.
    """
    return message_template_service.create(db, obj_in)

@router.put("/{id}", response_model=MessageTemplate)
def update_message_template(id: int, obj_in: MessageTemplateUpdate, db: Session = Depends(get_db)):
    """
    Update an existing MessageTemplate record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated MessageTemplate record.
    """
    return message_template_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_message_template(id: int, db: Session = Depends(get_db)):
    """
    Delete a MessageTemplate record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return message_template_service.delete(db, id)
