# ER-ServiceDesk/app/crud/message_template.py
"""
Database access layer for a reusable template for a ticket's notes, whether internal or emailed to the customer.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.message_template import MessageTemplate
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateUpdate

class MessageTemplateCRUD:
    """Direct database access for MessageTemplate records."""

    def get(self, db: Session, id: int) -> MessageTemplate | None:
        return db.query(MessageTemplate).filter(MessageTemplate.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(MessageTemplate).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: MessageTemplateCreate) -> MessageTemplate:
        obj = MessageTemplate(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: MessageTemplate, obj_in: MessageTemplateUpdate) -> MessageTemplate:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(MessageTemplate).filter(MessageTemplate.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_message_template = MessageTemplateCRUD()
