# ER-ServiceDesk/app/crud/location.py
# CRUD operations for the Location model.
"""
Database access layer for named physical locations.
"""

from sqlalchemy.orm import Session
from app.models.location import Location
from app.schemas.location import LocationCreate, LocationUpdate

class LocationCRUD:
    """Direct database access for Location records."""

    def get(self, db: Session, id: int) -> Location | None:
        """
        Fetch a single Location by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Location instance, or None if not found.
        """
        return db.query(Location).filter(Location.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Location records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Location instances.
        """
        return db.query(Location).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: LocationCreate) -> Location:
        """
        Insert a new Location record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Location instance.
        """
        obj = Location(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Location, obj_in: LocationUpdate) -> Location:
        """
        Apply a partial update to an existing Location record.

        Args:
            db: Active database session.
            db_obj: The existing Location instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Location instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Location record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Location).filter(Location.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_location = LocationCRUD()
