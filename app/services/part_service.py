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
from fastapi import HTTPException, status
from app.crud.part import crud_part
from app.models.part_location import PartLocation
from app.schemas.part import PartCreate, PartUpdate
from app.schemas.part_location import PartLocationInput
from app.services.system_setting_service import system_setting_service


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

    def deduction_location_id(self, db: Session) -> int:
        """
        Reads the Admin-configured part_deduction_location_id
        SystemSetting. Shared by every code path that bills a part on
        an Invoice -- both invoice_service.add_line_item() (a part
        added directly) and quote_service.convert_to_invoice() (a part
        that arrives via a converted quote) -- so there's a single,
        real implementation rather than two that could drift apart.

        Raises:
            HTTPException: 400 if no deduction location is configured
                -- deliberately a hard failure rather than silently
                skipping the deduction, since a part being billed
                without inventory actually moving would be a silent
                data-integrity problem, not just a missing convenience.
        """
        location_id = system_setting_service.get_int(db, "part_deduction_location_id", 0)
        if not location_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No part deduction location is configured -- set one in Settings -> System Settings before billing parts.",
            )
        return location_id

    def deduct_stock(self, db: Session, part_id: int, quantity: int):
        """Creates a zero-quantity PartLocation row at the deduction location first if none exists yet, then deducts."""
        location_id = self.deduction_location_id(db)
        part_location = db.query(PartLocation).filter(
            PartLocation.part_id == part_id, PartLocation.location_id == location_id,
        ).first()
        if not part_location:
            part_location = PartLocation(part_id=part_id, location_id=location_id, quantity=0)
            db.add(part_location)
        part_location.quantity -= quantity
        db.commit()

    def restore_stock(self, db: Session, part_id: int, quantity: int):
        """Reverses a prior deduction -- called when a part line item is removed, or its quantity is reduced."""
        location_id = self.deduction_location_id(db)
        part_location = db.query(PartLocation).filter(
            PartLocation.part_id == part_id, PartLocation.location_id == location_id,
        ).first()
        if not part_location:
            part_location = PartLocation(part_id=part_id, location_id=location_id, quantity=0)
            db.add(part_location)
        part_location.quantity += quantity
        db.commit()

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
