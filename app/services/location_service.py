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
        return crud_location.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_location.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: LocationCreate):
        return crud_location.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: LocationUpdate):
        db_obj = crud_location.get(db, id)
        return crud_location.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        return crud_location.delete(db, id)

location_service = LocationService()
