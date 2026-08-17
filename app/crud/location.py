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
        return db.query(Location).filter(Location.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Location).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: LocationCreate) -> Location:
        obj = Location(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Location, obj_in: LocationUpdate) -> Location:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Location).filter(Location.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_location = LocationCRUD()
