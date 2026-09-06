# ER-ServiceDesk/app/services/tax_rate_service.py
"""
Business logic for a named tax rate.
"""

from sqlalchemy.orm import Session
from app.crud.tax_rate import crud_tax_rate
from app.schemas.tax_rate import TaxRateCreate, TaxRateUpdate
from app.services.audit_log_service import audit_log_service


class TaxRateService:
    """Business logic for TaxRate operations."""

    def get(self, db: Session, id: int):
        return crud_tax_rate.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return crud_tax_rate.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TaxRateCreate, current_user_id: int):
        new_tax_rate = crud_tax_rate.create(db, obj_in)
        audit_log_service.log(
            db, "tax_rate_created", "tax_rate", new_tax_rate.id, user_id=current_user_id,
            details=f"Created tax rate: {new_tax_rate.name} ({new_tax_rate.percentage}%)",
        )
        return new_tax_rate

    def update(self, db: Session, id: int, obj_in: TaxRateUpdate, current_user_id: int):
        db_obj = crud_tax_rate.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)
        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_tax_rate.update(db, db_obj, obj_in)

        if changed_fields:
            audit_log_service.log(
                db, "tax_rate_updated", "tax_rate", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

    def delete(self, db: Session, id: int, current_user_id: int):
        """Safe even if referenced by existing quotes/invoices -- they snapshot their own name/amount and the foreign key is ON DELETE SET NULL."""
        db_obj = crud_tax_rate.get(db, id)
        deleted_name = db_obj.name if db_obj else None

        result = crud_tax_rate.delete(db, id)

        audit_log_service.log(
            db, "tax_rate_deleted", "tax_rate", id, user_id=current_user_id,
            details=f"Deleted tax rate: {deleted_name}" if deleted_name else None,
        )

        return result

tax_rate_service = TaxRateService()
