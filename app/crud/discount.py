# ER-ServiceDesk/app/crud/discount.py
"""
Database access layer for a named discount category.
"""

from sqlalchemy.orm import Session
from app.models.discount import Discount
from app.schemas.discount import DiscountCreate, DiscountUpdate

class DiscountCRUD:
    """Direct database access for Discount records."""

    def get(self, db: Session, id: int) -> Discount | None:
        return db.query(Discount).filter(Discount.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return db.query(Discount).order_by(Discount.name).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: DiscountCreate) -> Discount:
        obj = Discount(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: Discount, obj_in: DiscountUpdate) -> Discount:
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        obj = db.query(Discount).filter(Discount.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_discount = DiscountCRUD()
