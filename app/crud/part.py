# ER-ServiceDesk/app/crud/part.py
# CRUD operations for the Part model.
"""
Database access layer for consumable parts stock. Rejects duplicate SKUs,
mirroring the duplicate-check pattern used for Asset serial numbers.
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.part import Part
from app.schemas.part import PartCreate, PartUpdate

class PartCRUD:
    """Direct database access for Part records."""

    def get(self, db: Session, id: int) -> Part | None:
        return db.query(Part).filter(Part.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        return db.query(Part).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: PartCreate) -> Part:
        """
        Insert a new Part record, rejecting duplicate SKUs. `locations`
        is handled by the service layer, not here -- this only creates
        the Part row itself.

        Raises:
            HTTPException: 400 if a part with the same sku already exists.
        """
        if obj_in.sku:
            existing = db.query(Part).filter(Part.sku == obj_in.sku).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Part with this SKU already exists",
                )

        obj = Part(**obj_in.model_dump(exclude={"locations"}))
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Part, obj_in: PartUpdate) -> Part:
        """`locations` is handled by the service layer, not here -- this only updates the Part row's own columns."""
        for field, value in obj_in.model_dump(exclude_unset=True, exclude={"locations"}).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Part).filter(Part.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_part = PartCRUD()
