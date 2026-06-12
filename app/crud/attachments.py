# ER-ServiceDesk/app/crud/attachment.py
# CRUD operations for the Attachment model.
#
# Provides database access for creating, reading, updating, and deleting Attachment records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.attachment import Attachment
from app.schemas.attachment import AttachmentCreate, AttachmentUpdate

class AttachmentCRUD:
    # Retrieves a single Attachment by ID.
    def get(self, db: Session, id: int) -> Attachment | None:
        """
        Returns a single Attachment instance matching the given ID.
        """
        return db.query(Attachment).filter(Attachment.id == id).first()

    # Retrieves multiple Attachment records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Attachment records with pagination support.
        """
        return db.query(Attachment).offset(skip).limit(limit).all()

    # Creates a new Attachment record.
    def create(self, db: Session, obj_in: AttachmentCreate) -> Attachment:
        """
        Creates a new Attachment using the provided input schema.
        """
        obj = Attachment(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Attachment record.
    def update(self, db: Session, db_obj: Attachment, obj_in: AttachmentUpdate) -> Attachment:
        """
        Updates the given Attachment instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes an Attachment record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Attachment instance matching the given ID.
        """
        obj = db.query(Attachment).filter(Attachment.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_attachment = AttachmentCRUD()
