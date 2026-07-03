# ER-ServiceDesk/app/routes/attachments.py
# API routes for Attachment operations.
"""
REST endpoints for a file uploaded and linked to a support ticket.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.attachment_service import attachment_service
from app.schemas.attachment import Attachment, AttachmentCreate, AttachmentUpdate

router = APIRouter(prefix="/attachments", tags=["attachments"])

@router.get("/", response_model=list[Attachment])
def list_attachments(db: Session = Depends(get_db)):
    """
    List a file uploaded and linked to a support ticket, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Attachment records.
    """
    return attachment_service.get_multi(db)

@router.get("/{id}", response_model=Attachment)
def get_attachment(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Attachment record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Attachment record.
    """
    return attachment_service.get(db, id)

@router.post("/", response_model=Attachment)
def create_attachment(obj_in: AttachmentCreate, db: Session = Depends(get_db)):
    """
    Create a new Attachment record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created Attachment record.
    """
    return attachment_service.create(db, obj_in)

@router.put("/{id}", response_model=Attachment)
def update_attachment(id: int, obj_in: AttachmentUpdate, db: Session = Depends(get_db)):
    """
    Update an existing Attachment record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated Attachment record.
    """
    return attachment_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_attachment(id: int, db: Session = Depends(get_db)):
    """
    Delete a Attachment record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return attachment_service.delete(db, id)
