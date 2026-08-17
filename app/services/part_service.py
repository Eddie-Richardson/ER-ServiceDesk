# ER-ServiceDesk/app/services/part_service.py
# Service layer for Part.

"""
Business logic for Part operations. Route handlers call into this
layer rather than the CRUD layer directly.

Owns the "replace this part's stock breakdown" logic that crud_part
deliberately doesn't handle -- creating/updating the Part row itself is
a CRUD concern, but reconciling the part_locations rows against a new
list from the client is business logic that belongs here.
"""

from sqlalchemy.orm import Session
from app.crud.part import crud_part
from app.models.part_location import PartLocation
from app.schemas.part import PartCreate, PartUpdate
from app.schemas.part_location import PartLocationInput


class PartService:
    """Business logic for Part operations."""

    def get(self, db: Session, id: int):
        return crud_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return crud_part.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PartCreate):
        """Applies the initial stock breakdown (obj_in.locations) after creating the Part row itself."""
        obj = crud_part.create(db, obj_in)
        self._replace_locations(db, obj.id, obj_in.locations)
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, obj_in: PartUpdate):
        """If a new `locations` list is given, it replaces the part's entire stock breakdown; if omitted, the existing breakdown is left as-is."""
        db_obj = crud_part.get(db, id)
        db_obj = crud_part.update(db, db_obj, obj_in)
        if obj_in.locations is not None:
            self._replace_locations(db, id, obj_in.locations)
            db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int):
        """Its part_locations rows are removed automatically via the model's cascade="all, delete-orphan"."""
        return crud_part.delete(db, id)

    def _replace_locations(self, db: Session, part_id: int, locations: list[PartLocationInput]):
        """
        Replaces every part_locations row for the given part with the
        given list. Delete-then-recreate rather than diffing individual
        rows -- a part's location spread is always a short list, so
        this stays simple and correct rather than chasing edge cases in
        a more "efficient" merge.
        """
        db.query(PartLocation).filter(PartLocation.part_id == part_id).delete()
        for entry in locations:
            db.add(PartLocation(
                part_id=part_id,
                location_id=entry.location_id,
                quantity=entry.quantity,
            ))
        db.commit()


part_service = PartService()
