# ER-ServiceDesk/app/services/discount_service.py
# Service layer for Discount.
"""
Business logic for a named discount category.
"""

from sqlalchemy.orm import Session
from app.crud.discount import crud_discount
from app.schemas.discount import DiscountCreate, DiscountUpdate
from app.services.audit_log_service import audit_log_service


class DiscountService:
    """Business logic for Discount operations."""

    def get(self, db: Session, id: int):
        return crud_discount.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return crud_discount.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: DiscountCreate, current_user_id: int):
        new_discount = crud_discount.create(db, obj_in)
        audit_log_service.log(
            db, "discount_created", "discount", new_discount.id, user_id=current_user_id,
            details=f"Created discount: {new_discount.name} ({new_discount.percentage}%)",
        )
        return new_discount

    def update(self, db: Session, id: int, obj_in: DiscountUpdate, current_user_id: int):
        db_obj = crud_discount.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)
        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_discount.update(db, db_obj, obj_in)

        if changed_fields:
            audit_log_service.log(
                db, "discount_updated", "discount", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

    def delete(self, db: Session, id: int, current_user_id: int):
        """Safe even if referenced by existing quotes/invoices -- they snapshot their own name/amount and the foreign key is ON DELETE SET NULL."""
        db_obj = crud_discount.get(db, id)
        deleted_name = db_obj.name if db_obj else None

        result = crud_discount.delete(db, id)

        audit_log_service.log(
            db, "discount_deleted", "discount", id, user_id=current_user_id,
            details=f"Deleted discount: {deleted_name}" if deleted_name else None,
        )

        return result

discount_service = DiscountService()
