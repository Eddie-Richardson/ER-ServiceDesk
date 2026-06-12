# ER-ServiceDesk/app/routes/message_templates.py
# API routes for MessageTemplate operations.
#
# Exposes REST endpoints for interacting with MessageTemplate records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.message_template_service import message_template_service
from app.schemas.message_template import MessageTemplate, MessageTemplateCreate, MessageTemplateUpdate

router = APIRouter(prefix="/message_templates", tags=["message_templates"])

@router.get("/", response_model=list[MessageTemplate])
def list_message_templates(db: Session = Depends(get_db)):
    """
    Returns a list of MessageTemplate records.
    """
    return message_template_service.get_multi(db)

@router.get("/{id}", response_model=MessageTemplate)
def get_message_template(id: int, db: Session = Depends(get_db)):
    """
    Returns a single MessageTemplate record by ID.
    """
    return message_template_service.get(db, id)

@router.post("/", response_model=MessageTemplate)
def create_message_template(obj_in: MessageTemplateCreate, db: Session = Depends(get_db)):
    """
    Creates a new MessageTemplate record.
    """
    return message_template_service.create(db, obj_in)

@router.put("/{id}", response_model=MessageTemplate)
def update_message_template(id: int, obj_in: MessageTemplateUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing MessageTemplate record.
    """
    return message_template_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_message_template(id: int, db: Session = Depends(get_db)):
    """
    Deletes a MessageTemplate record by ID.
    """
    return message_template_service.delete(db, id)
