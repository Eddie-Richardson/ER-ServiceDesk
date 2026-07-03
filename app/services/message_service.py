# ER-ServiceDesk/app/services/message_service.py
# Service layer for Message.
"""
Business logic for a customer-facing message exchanged on a ticket (e.g. via email).

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.message import crud_message
from app.schemas.message import MessageCreate, MessageUpdate

class MessageService:
    """Business logic for Message operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Message by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Message instance, or None if not found.
        """
        return crud_message.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Message records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Message instances.
        """
        return crud_message.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: MessageCreate):
        """
        Create a new Message using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Message instance.
        """
        return crud_message.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: MessageUpdate):
        """
        Update an existing Message using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Message instance.
        """
        db_obj = crud_message.get(db, id)
        return crud_message.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Message by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_message.delete(db, id)

message_service = MessageService()
