# ER-ServiceDesk/app/crud/background_job.py
# CRUD operations for the BackgroundJob model.
#
# Provides database access for creating, reading, updating, and deleting BackgroundJob records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.background_job import BackgroundJob
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobCRUD:
    # Retrieves a single BackgroundJob by ID.
    def get(self, db: Session, id: int) -> BackgroundJob | None:
        """
        Returns a single BackgroundJob instance matching the given ID.
        """
        return db.query(BackgroundJob).filter(BackgroundJob.id == id).first()

    # Retrieves multiple BackgroundJob records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of BackgroundJob records with pagination support.
        """
        return db.query(BackgroundJob).offset(skip).limit(limit).all()

    # Creates a new BackgroundJob record.
    def create(self, db: Session, obj_in: BackgroundJobCreate) -> BackgroundJob:
        """
        Creates a new BackgroundJob using the provided input schema.
        """
        obj = BackgroundJob(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing BackgroundJob record.
    def update(self, db: Session, db_obj: BackgroundJob, obj_in: BackgroundJobUpdate) -> BackgroundJob:
        """
        Updates the given BackgroundJob instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes a BackgroundJob record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the BackgroundJob instance matching the given ID.
        """
        obj = db.query(BackgroundJob).filter(BackgroundJob.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_background_job = BackgroundJobCRUD()
