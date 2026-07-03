# ER-ServiceDesk/app/services/status_history_service.py
# Service layer for StatusHistory.
"""
Business logic for an audit trail entry for a ticket status transition.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.status_history import crud_status_history
from app.schemas.status_history import StatusHistoryCreate, StatusHistoryUpdate

class StatusHistoryService:
    """Business logic for StatusHistory operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single StatusHistory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching StatusHistory instance, or None if not found.
        """
        return crud_status_history.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of StatusHistory records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of StatusHistory instances.
        """
        return crud_status_history.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: StatusHistoryCreate):
        """
        Create a new StatusHistory using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created StatusHistory instance.
        """
        return crud_status_history.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: StatusHistoryUpdate):
        """
        Update an existing StatusHistory using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated StatusHistory instance.
        """
        db_obj = crud_status_history.get(db, id)
        return crud_status_history.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a StatusHistory by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_status_history.delete(db, id)

status_history_service = StatusHistoryService()
