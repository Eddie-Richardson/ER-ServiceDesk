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
        """
        Fetch a single Part by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Part instance, or None if not found.
        """
        return crud_part.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of Part records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Part instances.
        """
        return crud_part.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: PartCreate):
        """
        Create a new Part using validated input data, then apply its
        initial stock breakdown.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record, including
                the initial `locations` breakdown.

        Returns:
            The newly created Part instance, with locations applied.
        """
        obj = crud_part.create(db, obj_in)
        self._replace_locations(db, obj.id, obj_in.locations)
        db.refresh(obj)
        return obj

    def update(self, db: Session, id: int, obj_in: PartUpdate):
        """
        Update an existing Part using validated input data. If a new
        `locations` list is given, it replaces the part's entire stock
        breakdown; if omitted, the existing breakdown is left as-is.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated Part instance.
        """
        db_obj = crud_part.get(db, id)
        db_obj = crud_part.update(db, db_obj, obj_in)
        if obj_in.locations is not None:
            self._replace_locations(db, id, obj_in.locations)
            db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int):
        """
        Delete a Part by ID. Its part_locations rows are removed
        automatically via the model's cascade="all, delete-orphan".

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_part.delete(db, id)

    def _replace_locations(self, db: Session, part_id: int, locations: list[PartLocationInput]):
        """
        Replaces every part_locations row for the given part with the
        given list. Delete-then-recreate rather than diffing individual
        rows -- a part's location spread is always a short list, so
        this stays simple and correct rather than chasing edge cases in
        a more "efficient" merge.

        Args:
            db: Active database session.
            part_id: The Part whose stock breakdown is being replaced.
            locations: The new full breakdown to apply.
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
