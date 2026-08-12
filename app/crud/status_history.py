# ER-ServiceDesk/app/crud/status_history.py
# CRUD operations for the StatusHistory model -- get and create only.
"""
Database access layer for a ticket's status change history.

Deliberately no update() or delete() -- this is meant to be an
immutable audit trail. Only get/get_multi/create exist, matching the
service and route layers above this (see status_history_service.py,
routes/status_histories.py), so there's no path anywhere in the stack
that could rewrite or erase a recorded status change.
"""

from sqlalchemy.orm import Session
from app.models.status_history import StatusHistory
from app.schemas.status_history import StatusHistoryCreate

class StatusHistoryCRUD:
    """Direct database access for StatusHistory records -- read and create only."""

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
        Insert a new StatusHistory record. Only ever called internally
        by ticket_service.py when a ticket's status_id genuinely
        changes -- never directly from a route.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed StatusHistory instance.
        """
        obj = StatusHistory(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

crud_status_history = StatusHistoryCRUD()
