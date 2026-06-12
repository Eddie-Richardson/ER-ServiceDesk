# ER-ServiceDesk/app/services/audit_log_service.py
# Service layer for AuditLog.
#
# Provides business logic for AuditLog operations.
# Coordinates CRUD operations and applies system rules.
# Contains no API routing; used by route handlers.

# ---------------------------------------------------------------------------
# Service Logic
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate

class AuditLogService:
    # Retrieves a single AuditLog by ID.
    def get(self, db: Session, id: int):
        """
        Returns a single AuditLog instance.
        """
        return crud_audit_log.get(db, id)

    # Retrieves multiple AuditLog records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of AuditLog records.
        """
        return crud_audit_log.get_multi(db, skip, limit)

    # Creates a new AuditLog.
    def create(self, db: Session, obj_in: AuditLogCreate):
        """
        Creates a new AuditLog using validated input data.
        """
        return crud_audit_log.create(db, obj_in)

    # Updates an existing AuditLog.
    def update(self, db: Session, id: int, obj_in: AuditLogUpdate):
        """
        Updates an existing AuditLog using validated input data.
        """
        db_obj = crud_audit_log.get(db, id)
        return crud_audit_log.update(db, db_obj, obj_in)

    # Deletes an AuditLog by ID.
    def delete(self, db: Session, id: int):
        """
        Deletes an AuditLog instance.
        """
        return crud_audit_log.delete(db, id)

audit_log_service = AuditLogService()
