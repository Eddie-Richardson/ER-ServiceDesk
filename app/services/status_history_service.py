# ER-ServiceDesk/app/services/status_history_service.py
# Service layer for StatusHistory.
#
# Provides business logic for StatusHistory operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.status_history import crud_status_history
from app.schemas.status_history import StatusHistoryCreate, StatusHistoryUpdate

class StatusHistoryService:
    # Retrieves a single StatusHistory by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single StatusHistory instance.
        """
        return crud_status_history.get(db, id)

    # Retrieves multiple StatusHistory records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of StatusHistory records.
        """
        return crud_status_history.get_multi(db, skip, limit)

    # Creates a new StatusHistory.
    def create(self, db: Session, obj_in: StatusHistoryCreate):
        """
        Creates a new StatusHistory using validated input data.
        """
        return crud_status_history.create(db, obj_in)

    # Updates an existing StatusHistory.
    def update(self, db: Session, id: int, obj_in: StatusHistoryUpdate):
        """
        Updates an existing StatusHistory using validated input data.
        """
        db_obj = crud_status_history.get(db, id)
        return crud_status_history.update(db, db_obj, obj_in)

    # Deletes a StatusHistory by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a StatusHistory instance.
        """
        return crud_status_history.delete(db, id)

status_history_service = StatusHistoryService()
