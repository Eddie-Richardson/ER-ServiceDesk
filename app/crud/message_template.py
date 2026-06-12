# ER-ServiceDesk/app/crud/message_template.py
# CRUD operations for the MessageTemplate model.
#
# Provides database access for creating, reading, updating, and deleting MessageTemplate records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.message_template import MessageTemplate
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateUpdate

class MessageTemplateCRUD:
    # Retrieves a single MessageTemplate by ID.
    def get(self, db: Session, id: int) -> MessageTemplate | None:
        """
        Returns a single MessageTemplate instance matching the given ID.
        """
        return db.query(MessageTemplate).filter(MessageTemplate.id == id).first()

    # Retrieves multiple MessageTemplate records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of MessageTemplate records with pagination support.
        """
        return db.query(MessageTemplate).offset(skip).limit(limit).all()

    # Creates a new MessageTemplate record.
    def create(self, db: Session, obj_in: MessageTemplateCreate) -> MessageTemplate:
        """
       Creates a new MessageTemplate using the provided input schema.
        """
        obj = MessageTemplate(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing MessageTemplate record.
    def update(self, db: Session, db_obj: MessageTemplate, obj_in: MessageTemplateUpdate) -> MessageTemplate:
        """
        Updates the given MessageTemplate instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a MessageTemplate record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the MessageTemplate instance matching the given ID.
        """
        obj = db.query(MessageTemplate).filter(MessageTemplate.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_message_template = MessageTemplateCRUD()
