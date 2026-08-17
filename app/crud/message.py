# ER-ServiceDesk/app/crud/message.py
# CRUD operations for the Message model.
"""
Database access layer for a ticket's note/conversation history --
internal notes and customer-facing email exchange alike.
"""

from sqlalchemy.orm import Session
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate

class MessageCRUD:
    """Direct database access for Message records."""

    def get(self, db: Session, id: int) -> Message | None:
        return db.query(Message).filter(Message.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Message).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: MessageCreate) -> Message:
        obj = Message(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Message, obj_in: MessageUpdate) -> Message:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Message).filter(Message.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_message = MessageCRUD()
