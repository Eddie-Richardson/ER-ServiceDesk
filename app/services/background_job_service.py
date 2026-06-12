# ER-ServiceDesk/app/services/background_job_service.py
# Service layer for BackgroundJob.
#
# Provides business logic for BackgroundJob operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.background_job import crud_background_job
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobService:
    # Retrieves a single BackgroundJob by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single BackgroundJob instance.
        """
        return crud_background_job.get(db, id)

    # Retrieves multiple BackgroundJob records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of BackgroundJob records.
        """
        return crud_background_job.get_multi(db, skip, limit)

    # Creates a new BackgroundJob.
    def create(self, db: Session, obj_in: BackgroundJobCreate):
        """
        Creates a new BackgroundJob using validated input data.
        """
        return crud_background_job.create(db, obj_in)

    # Updates an existing BackgroundJob.
    def update(self, db: Session, id: int, obj_in: BackgroundJobUpdate):
        """
        Updates an existing BackgroundJob using validated input data.
        """
        db_obj = crud_background_job.get(db, id)
        return crud_background_job.update(db, db_obj, obj_in)

    # Deletes a BackgroundJob by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes a BackgroundJob instance.
        """
        return crud_background_job.delete(db, id)

background_job_service = BackgroundJobService()
