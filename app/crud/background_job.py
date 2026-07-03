# ER-ServiceDesk/app/crud/background_job.py
# CRUD operations for the BackgroundJob model.
"""
Database access layer for an asynchronous job tracked for the RQ worker system.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.background_job import BackgroundJob
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobCRUD:
    """Direct database access for BackgroundJob records."""

    def get(self, db: Session, id: int) -> BackgroundJob | None:
        """
        Fetch a single BackgroundJob by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching BackgroundJob instance, or None if no record exists.
        """
        return db.query(BackgroundJob).filter(BackgroundJob.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple BackgroundJob records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of BackgroundJob instances.
        """
        return db.query(BackgroundJob).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: BackgroundJobCreate) -> BackgroundJob:
        """
        Insert a new BackgroundJob record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed BackgroundJob instance.
        """
        obj = BackgroundJob(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: BackgroundJob, obj_in: BackgroundJobUpdate) -> BackgroundJob:
        """
        Apply a partial update to an existing BackgroundJob record.

        Args:
            db: Active database session.
            db_obj: The existing BackgroundJob instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed BackgroundJob instance.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a BackgroundJob record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(BackgroundJob).filter(BackgroundJob.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_background_job = BackgroundJobCRUD()
