# ER-ServiceDesk/app/crud/discount.py
# CRUD operations for the Discount model.
"""
Database access layer for a named discount category.
"""

from sqlalchemy.orm import Session
from app.models.discount import Discount
from app.schemas.discount import DiscountCreate, DiscountUpdate

class DiscountCRUD:
    """Direct database access for Discount records."""

    def get(self, db: Session, id: int) -> Discount | None:
        """
        Fetch a single Discount by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Discount instance, or None if no record exists.
        """
        return db.query(Discount).filter(Discount.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        """
        Fetch multiple Discount records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Discount instances.
        """
        return db.query(Discount).order_by(Discount.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: DiscountCreate) -> Discount:
        """
        Insert a new Discount record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed Discount instance.
        """
        obj = Discount(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Discount, obj_in: DiscountUpdate) -> Discount:
        """
        Apply a partial update to an existing Discount record.

        Args:
            db: Active database session.
            db_obj: The existing Discount instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed Discount instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a Discount record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(Discount).filter(Discount.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_discount = DiscountCRUD()
