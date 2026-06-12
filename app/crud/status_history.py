# ER-ServiceDesk/app/crud/status_history.py
# CRUD operations for the StatusHistory model.
#
# Provides database access for creating, reading, updating, and deleting StatusHistory records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.status_history import StatusHistory
from app.schemas.status_history import StatusHistoryCreate, StatusHistoryUpdate

class StatusHistoryCRUD:
    # Retrieves a single StatusHistory by ID.
    def get(self, db: Session, id: int) -> StatusHistory | None:
        """
        Returns a single StatusHistory instance matching the given ID.
        """
        return db.query(StatusHistory).filter(StatusHistory.id == id).first()

    # Retrieves multiple StatusHistory records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of StatusHistory records with pagination support.
        """
        return db.query(StatusHistory).offset(skip).limit(limit).all()

    # Creates a new StatusHistory record.
    def create(self, db: Session, obj_in: StatusHistoryCreate) -> StatusHistory:
        """
        Creates a new StatusHistory using the provided input schema.
        """
        obj = StatusHistory(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing StatusHistory record.
    def update(self, db: Session, db_obj: StatusHistory, obj_in: StatusHistoryUpdate) -> StatusHistory:
        """
        Updates the given StatusHistory instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a StatusHistory record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the StatusHistory instance matching the given ID.
        """
        obj = db.query(StatusHistory).filter(StatusHistory.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_status_history = StatusHistoryCRUD()
