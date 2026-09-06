# ER-ServiceDesk/app/services/service_service.py
"""
Business logic for a billable service the shop offers.
"""

from sqlalchemy.orm import Session
from app.crud.service import crud_service
from app.schemas.service import ServiceCreate, ServiceUpdate
from app.services.audit_log_service import audit_log_service


class ServiceCatalogService:
    """Business logic for Service (billable service catalog) operations."""

    def get(self, db: Session, id: int):
        return crud_service.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 200):
        return crud_service.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: ServiceCreate, current_user_id: int):
        new_service = crud_service.create(db, obj_in)
        audit_log_service.log(
            db, "service_created", "service", new_service.id, user_id=current_user_id,
            details=f"Created service: {new_service.name} (${new_service.price})",
        )
        return new_service

    def update(self, db: Session, id: int, obj_in: ServiceUpdate, current_user_id: int):
        db_obj = crud_service.get(db, id)
        update_data = obj_in.model_dump(exclude_unset=True)
        changed_fields = [field for field in update_data if getattr(db_obj, field) != update_data[field]]

        updated = crud_service.update(db, db_obj, obj_in)

        if changed_fields:
            audit_log_service.log(
                db, "service_updated", "service", id, user_id=current_user_id,
                details=f"Changed fields: {', '.join(changed_fields)}",
            )

        return updated

    def delete(self, db: Session, id: int, current_user_id: int):
        """Safe even if referenced by existing line items -- they snapshot their own name/price and the foreign key is ON DELETE SET NULL, so this never breaks historical billing records."""
        db_obj = crud_service.get(db, id)
        deleted_name = db_obj.name if db_obj else None

        result = crud_service.delete(db, id)

        audit_log_service.log(
            db, "service_deleted", "service", id, user_id=current_user_id,
            details=f"Deleted service: {deleted_name}" if deleted_name else None,
        )

        return result

service_service = ServiceCatalogService()
