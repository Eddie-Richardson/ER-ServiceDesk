# ER-ServiceDesk/app/services/tax_rate_service.py
# Service layer for TaxRate.
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
        """
        Fetch a single TaxRate by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching TaxRate instance, or None if not found.
        """
        return crud_tax_rate.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        """
        Fetch a page of TaxRate records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of TaxRate instances.
        """
        return crud_tax_rate.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: TaxRateCreate, current_user_id: int):
        """
        Create a new TaxRate.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.
            current_user_id: The user creating this tax rate -- recorded
                in the audit trail.

        Returns:
            The newly created TaxRate instance.
        """
        new_tax_rate = crud_tax_rate.create(db, obj_in)
        audit_log_service.log(
            db, "tax_rate_created", "tax_rate", new_tax_rate.id, user_id=current_user_id,
            details=f"Created tax rate: {new_tax_rate.name} ({new_tax_rate.percentage}%)",
        )
        return new_tax_rate

    def update(self, db: Session, id: int, obj_in: TaxRateUpdate, current_user_id: int):
        """
        Update an existing TaxRate.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated TaxRate instance.
        """
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
        """
        Delete a TaxRate by ID. Safe even if referenced by existing
        quotes/invoices -- they snapshot their own name/amount and the
        foreign key is ON DELETE SET NULL.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user_id: The user performing this deletion --
                recorded in the audit trail.
        """
        db_obj = crud_tax_rate.get(db, id)
        deleted_name = db_obj.name if db_obj else None

        result = crud_tax_rate.delete(db, id)

        audit_log_service.log(
            db, "tax_rate_deleted", "tax_rate", id, user_id=current_user_id,
            details=f"Deleted tax rate: {deleted_name}" if deleted_name else None,
        )

        return result

tax_rate_service = TaxRateService()
