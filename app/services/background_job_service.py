# ER-ServiceDesk/app/services/background_job_service.py
# Service layer for BackgroundJob.
"""
Business logic for an asynchronous job tracked for the RQ worker system.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.background_job import crud_background_job
from app.schemas.background_job import BackgroundJobCreate, BackgroundJobUpdate

class BackgroundJobService:
    """Business logic for BackgroundJob operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single BackgroundJob by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching BackgroundJob instance, or None if not found.
        """
        return crud_background_job.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of BackgroundJob records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of BackgroundJob instances.
        """
        return crud_background_job.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: BackgroundJobCreate):
        """
        Create a new BackgroundJob using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created BackgroundJob instance.
        """
        return crud_background_job.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: BackgroundJobUpdate):
        """
        Update an existing BackgroundJob using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated BackgroundJob instance.
        """
        db_obj = crud_background_job.get(db, id)
        return crud_background_job.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a BackgroundJob by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_background_job.delete(db, id)

background_job_service = BackgroundJobService()
