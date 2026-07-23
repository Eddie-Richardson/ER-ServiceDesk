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
        """
        Fetch a single Part by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Part instance, or None if not found.
        """
        return db.query(Part).filter(Part.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple Part records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Part instances.
        """
        return db.query(Part).offset(skip).limit(limit).all()

    def get_low_stock(self, db: Session):
        """
        Fetch every part whose total quantity (summed across every
        location it's stored at) is at or below its reorder threshold.

        Computed in Python rather than as a SQL WHERE clause, since
        quantity_on_hand is a computed property (summing part_locations
        rows) rather than a real column -- straightforward and correct
        at the scale of one shop's parts inventory.

        Args:
            db: Active database session.

        Returns:
            A list of Part instances that need reordering.
        """
        return [p for p in db.query(Part).all() if p.quantity_on_hand <= p.reorder_threshold]

    def create(self, db: Session, obj_in: PartCreate) -> Part:
        """
        Insert a new Part record, rejecting duplicate SKUs.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record. Its
                `locations` field is handled by the service layer, not
                here -- this only creates the Part row itself.

        Returns:
            The newly created, refreshed Part instance.

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
        """
        Apply a partial update to an existing Part record.

        Args:
            db: Active database session.
            db_obj: The existing Part instance to update.
            obj_in: Fields to change; unset fields are left untouched.
                Its `locations` field is handled by the service layer,
                not here -- this only updates the Part row's own columns.

        Returns:
            The updated, refreshed Part instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True, exclude={"locations"}).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Part record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Part).filter(Part.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_part = PartCRUD()
