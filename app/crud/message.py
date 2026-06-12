# ER-ServiceDesk/app/crud/message.py
# CRUD operations for the Message model.
#
# Provides database access for creating, reading, updating, and deleting Message records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate

class MessageCRUD:
    # Retrieves a single Message by ID.
    def get(self, db: Session, id: int) -> Message | None:
        """
        Returns a single Message instance matching the given ID.
        """
        return db.query(Message).filter(Message.id == id).first()

    # Retrieves multiple Message records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of Message records with pagination support.
        """
        return db.query(Message).offset(skip).limit(limit).all()

    # Creates a new Message record.
    def create(self, db: Session, obj_in: MessageCreate) -> Message:
        """
        Creates a new Message using the provided input schema.
        """
        obj = Message(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing Message record.
    def update(self, db: Session, db_obj: Message, obj_in: MessageUpdate) -> Message:
        """
        Updates the given Message instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a Message record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the Message instance matching the given ID.
        """
        obj = db.query(Message).filter(Message.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_message = MessageCRUD()
