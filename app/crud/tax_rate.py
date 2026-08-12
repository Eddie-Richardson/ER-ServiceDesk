# ER-ServiceDesk/app/crud/tax_rate.py
# CRUD operations for the TaxRate model.
"""
Database access layer for a named tax rate.
"""

from sqlalchemy.orm import Session
from app.models.tax_rate import TaxRate
from app.schemas.tax_rate import TaxRateCreate, TaxRateUpdate

class TaxRateCRUD:
    """Direct database access for TaxRate records."""

    def get(self, db: Session, id: int) -> TaxRate | None:
        """
        Fetch a single TaxRate by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TaxRate instance, or None if no record exists.
        """
        return db.query(TaxRate).filter(TaxRate.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        """
        Fetch multiple TaxRate records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TaxRate instances.
        """
        return db.query(TaxRate).order_by(TaxRate.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TaxRateCreate) -> TaxRate:
        """
        Insert a new TaxRate record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed TaxRate instance.
        """
        obj = TaxRate(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TaxRate, obj_in: TaxRateUpdate) -> TaxRate:
        """
        Apply a partial update to an existing TaxRate record.

        Args:
            db: Active database session.
            db_obj: The existing TaxRate instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed TaxRate instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a TaxRate record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(TaxRate).filter(TaxRate.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_tax_rate = TaxRateCRUD()
