# ER-ServiceDesk/app/crud/status_history.py
# CRUD operations for the StatusHistory model.
"""
Database access layer for an audit trail entry for a ticket status transition.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.status_history import StatusHistory
from app.schemas.status_history import StatusHistoryCreate, StatusHistoryUpdate

class StatusHistoryCRUD:
    """Direct database access for StatusHistory records."""

    def get(self, db: Session, id: int) -> StatusHistory | None:
        """
        Fetch a single StatusHistory by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching StatusHistory instance, or None if no record exists.
        """
        return db.query(StatusHistory).filter(StatusHistory.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple StatusHistory records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of StatusHistory instances.
        """
        return db.query(StatusHistory).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: StatusHistoryCreate) -> StatusHistory:
        """
        Insert a new StatusHistory record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed StatusHistory instance.
        """
        obj = StatusHistory(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: StatusHistory, obj_in: StatusHistoryUpdate) -> StatusHistory:
        """
        Apply a partial update to an existing StatusHistory record.

        Args:
            db: Active database session.
            db_obj: The existing StatusHistory instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed StatusHistory instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a StatusHistory record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(StatusHistory).filter(StatusHistory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_status_history = StatusHistoryCRUD()
