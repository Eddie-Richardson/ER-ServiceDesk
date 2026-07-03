# ER-ServiceDesk/app/services/attachment_service.py
# Service layer for Attachment.
"""
Business logic for a file uploaded and linked to a support ticket.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.attachment import crud_attachment
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate

class AttachmentService:
    """Business logic for Attachment operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Attachment by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Attachment instance, or None if not found.
        """
        return crud_attachment.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Attachment records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Attachment instances.
        """
        return crud_attachment.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AttachmentCreate):
        """
        Create a new Attachment using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Attachment instance.
        """
        return crud_attachment.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AttachmentUpdate):
        """
        Update an existing Attachment using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Attachment instance.
        """
        db_obj = crud_attachment.get(db, id)
        return crud_attachment.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Attachment by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_attachment.delete(db, id)

attachment_service = AttachmentService()
