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
        """
        Fetch a single Discount by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching Discount instance, or None if not found.
        """
        return crud_discount.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        """
        Fetch a page of Discount records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of Discount instances.
        """
        return crud_discount.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: DiscountCreate, current_user_id: int):
        """
        Create a new Discount.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.
            current_user_id: The user creating this discount -- recorded
                in the audit trail.

        Returns:
            The newly created Discount instance.
        """
        new_discount = crud_discount.create(db, obj_in)
        audit_log_service.log(
            db, "discount_created", "discount", new_discount.id, user_id=current_user_id,
            details=f"Created discount: {new_discount.name} ({new_discount.percentage}%)",
        )
        return new_discount

    def update(self, db: Session, id: int, obj_in: DiscountUpdate, current_user_id: int):
        """
        Update an existing Discount.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.
            current_user_id: The user making this change -- recorded
                in the audit trail.

        Returns:
            The updated Discount instance.
        """
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
        """
        Delete a Discount by ID. Safe even if referenced by existing
        quotes/invoices -- they snapshot their own name/amount and the
        foreign key is ON DELETE SET NULL.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
            current_user_id: The user performing this deletion --
                recorded in the audit trail.
        """
        db_obj = crud_discount.get(db, id)
        deleted_name = db_obj.name if db_obj else None

        result = crud_discount.delete(db, id)

        audit_log_service.log(
            db, "discount_deleted", "discount", id, user_id=current_user_id,
            details=f"Deleted discount: {deleted_name}" if deleted_name else None,
        )

        return result

discount_service = DiscountService()
