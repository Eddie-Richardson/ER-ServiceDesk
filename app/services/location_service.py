# ER-ServiceDesk/app/services/location_service.py
# Service layer for Location.
"""
Business logic for Location operations. Route handlers call into this
layer rather than the CRUD layer directly.
"""

from sqlalchemy.orm import Session
from app.crud.location import crud_location
from app.schemas.location import LocationCreate, LocationUpdate

class LocationService:
    """Business logic for Location operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single Location by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Location instance, or None if not found.
        """
        return crud_location.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Location records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Location instances.
        """
        return crud_location.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: LocationCreate):
        """
        Create a new Location using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created Location instance.
        """
        return crud_location.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: LocationUpdate):
        """
        Update an existing Location using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Location instance.
        """
        db_obj = crud_location.get(db, id)
        return crud_location.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a Location by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_location.delete(db, id)

location_service = LocationService()
