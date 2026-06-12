# ER-ServiceDesk/app/routes/attachments.py
# API routes for Attachment operations.
#
# Exposes REST endpoints for interacting with Attachment records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.attachment_service import attachment_service
from app.schemas.attachment import Attachment, AttachmentCreate, AttachmentUpdate

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.get("/", response_model=list[Attachment])
def list_attachments(db: Session = Depends(get_db)):
    """
    Returns a list of Attachment records.
    """
    return attachment_service.get_multi(db)

@router.get("/{id}", response_model=Attachment)
def get_attachment(id: int, db: Session = Depends(get_db)):
    """
    Returns a single Attachment record by ID.
    """
    return attachment_service.get(db, id)

@router.post("/", response_model=Attachment)
def create_attachment(obj_in: AttachmentCreate, db: Session = Depends(get_db)):
    """
    Creates a new Attachment record.
    """
    return attachment_service.create(db, obj_in)

@router.put("/{id}", response_model=Attachment)
def update_attachment(id: int, obj_in: AttachmentUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing Attachment record.
    """
    return attachment_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_attachment(id: int, db: Session = Depends(get_db)):
    """
    Deletes an Attachment record by ID.
    """
    return attachment_service.delete(db, id)
