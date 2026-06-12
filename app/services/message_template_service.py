# ER-ServiceDesk/app/services/message_template_service.py
# Service layer for MessageTemplate.
#
# Provides business logic for MessageTemplate operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.message_template import crud_message_template
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateUpdate

class MessageTemplateService:
    # Retrieves a single MessageTemplate by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single MessageTemplate instance.
        """
        return crud_message_template.get(db, id)

    # Retrieves multiple MessageTemplate records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of MessageTemplate records.
        """
        return crud_message_template.get_multi(db, skip, limit)

    # Creates a new MessageTemplate.
    def create(self, db: Session, obj_in: MessageTemplateCreate):
        """
        Creates a new MessageTemplate using validated input data.
        """
        return crud_message_template.create(db, obj_in)

    # Updates an existing MessageTemplate.
    def update(self, db: Session, id: int, obj_in: MessageTemplateUpdate):
        """
        Updates an existing MessageTemplate using validated input data.
        """
        db_obj = crud_message_template.get(db, id)
        return crud_message_template.update(db, db_obj, obj_in)

    # Deletes a MessageTemplate by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a MessageTemplate instance.
        """
        return crud_message_template.delete(db, id)

message_template_service = MessageTemplateService()
