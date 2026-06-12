# ER-ServiceDesk/app/services/message_service.py
# Service layer for Message.
#
# Provides business logic for Message operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.message import crud_message
from app.schemas.message import MessageCreate, MessageUpdate

class MessageService:
    # Retrieves a single Message by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single Message instance.
        """
        return crud_message.get(db, id)

    # Retrieves multiple Message records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Message records.
        """
        return crud_message.get_multi(db, skip, limit)

    # Creates a new Message.
    def create(self, db: Session, obj_in: MessageCreate):
        """
        Creates a new Message using validated input data.
        """
        return crud_message.create(db, obj_in)

    # Updates an existing Message.
    def update(self, db: Session, id: int, obj_in: MessageUpdate):
        """
        Updates an existing Message using validated input data.
        """
        db_obj = crud_message.get(db, id)
        return crud_message.update(db, db_obj, obj_in)

    # Deletes a Message by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a Message instance.
        """
        return crud_message.delete(db, id)

message_service = MessageService()
