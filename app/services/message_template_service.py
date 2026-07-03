# ER-ServiceDesk/app/services/message_template_service.py
# Service layer for MessageTemplate.
"""
Business logic for a reusable template for outbound emails/notifications.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.message_template import crud_message_template
from app.schemas.message_template import MessageTemplateCreate, MessageTemplateUpdate

class MessageTemplateService:
    """Business logic for MessageTemplate operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single MessageTemplate by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching MessageTemplate instance, or None if not found.
        """
        return crud_message_template.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of MessageTemplate records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of MessageTemplate instances.
        """
        return crud_message_template.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: MessageTemplateCreate):
        """
        Create a new MessageTemplate using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created MessageTemplate instance.
        """
        return crud_message_template.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: MessageTemplateUpdate):
        """
        Update an existing MessageTemplate using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated MessageTemplate instance.
        """
        db_obj = crud_message_template.get(db, id)
        return crud_message_template.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a MessageTemplate by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_message_template.delete(db, id)

message_template_service = MessageTemplateService()
