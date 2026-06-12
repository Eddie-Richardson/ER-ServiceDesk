# ER-ServiceDesk/app/services/attachment_service.py
# Service layer for Attachment.
#
# Provides business logic for Attachment operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.attachment import crud_attachment
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate

class AttachmentService:
    # Retrieves a single Attachment by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Attachment instance.
        """
        return crud_attachment.get(db, id)

    # Retrieves multiple Attachment records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Attachment records.
        """
        return crud_attachment.get_multi(db, skip, limit)

    # Creates a new Attachment.
    def create(self, db: Session, obj_in: AttachmentCreate):
        """
        Creates a new Attachment using validated input data.
        """
        return crud_attachment.create(db, obj_in)

    # Updates an existing Attachment.
    def update(self, db: Session, id: int, obj_in: AttachmentUpdate):
        """
        Updates an existing Attachment using validated input data.
        """
        db_obj = crud_attachment.get(db, id)
        return crud_attachment.update(db, db_obj, obj_in)

    # Deletes an Attachment by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes an Attachment instance.
        """
        return crud_attachment.delete(db, id)

attachment_service = AttachmentService()
