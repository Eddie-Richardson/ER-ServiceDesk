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
        return db.query(TaxRate).filter(TaxRate.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return db.query(TaxRate).order_by(TaxRate.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: TaxRateCreate) -> TaxRate:
        obj = TaxRate(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: TaxRate, obj_in: TaxRateUpdate) -> TaxRate:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(TaxRate).filter(TaxRate.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_tax_rate = TaxRateCRUD()
