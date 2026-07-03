# ER-ServiceDesk/app/crud/attachment.py
# CRUD operations for the Attachment model.
"""
Database access layer for a file uploaded and linked to a support ticket.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate

class AttachmentCRUD:
    """Direct database access for Attachment records."""

    def get(self, db: Session, id: int) -> Attachment | None:
        """
        Fetch a single Attachment by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Attachment instance, or None if no record exists.
        """
        return db.query(Attachment).filter(Attachment.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Attachment records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Attachment instances.
        """
        return db.query(Attachment).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AttachmentCreate) -> Attachment:
        """
        Insert a new Attachment record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Attachment instance.
        """
        obj = Attachment(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Attachment, obj_in: AttachmentUpdate) -> Attachment:
        """
        Apply a partial update to an existing Attachment record.

        Args:
            db: Active database session.
            db_obj: The existing Attachment instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Attachment instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Attachment record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Attachment).filter(Attachment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_attachment = AttachmentCRUD()
