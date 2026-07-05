# ER-ServiceDesk/app/crud/message.py
# CRUD operations for the Message model.
"""
Database access layer for a customer-facing message exchanged on a ticket (e.g. via email).

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate

class MessageCRUD:
    """Direct database access for Message records."""

    def get(self, db: Session, id: int) -> Message | None:
        """
        Fetch a single Message by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Message instance, or None if no record exists.
        """
        return db.query(Message).filter(Message.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Message records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Message instances.
        """
        return db.query(Message).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: MessageCreate) -> Message:
        """
        Insert a new Message record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Message instance.
        """
        obj = Message(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Message, obj_in: MessageUpdate) -> Message:
        """
        Apply a partial update to an existing Message record.

        Args:
            db: Active database session.
            db_obj: The existing Message instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Message instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Message record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Message).filter(Message.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_message = MessageCRUD()
