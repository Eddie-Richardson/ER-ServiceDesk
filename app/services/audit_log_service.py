# ER-ServiceDesk/app/services/audit_log_service.py
# Service layer for AuditLog.
"""
Business logic for a record of a user action or system event, for security review and compliance.

Coordinates CRUD operations and is where entity-specific rules should live
as they're added. Route handlers call into this layer rather than the CRUD
layer directly, so business rules stay in one place.
"""

from sqlalchemy.orm import Session
from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate

class AuditLogService:
    """Business logic for AuditLog operations."""

    def get(self, db: Session, id: int):
        """
        Fetch a single AuditLog by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching AuditLog instance, or None if not found.
        """
        return crud_audit_log.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch a page of AuditLog records.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of AuditLog instances.
        """
        return crud_audit_log.get_multi(db, skip, limit)

    def create(self, db: Session, obj_in: AuditLogCreate):
        """
        Create a new AuditLog using validated input data.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created AuditLog instance.
        """
        return crud_audit_log.create(db, obj_in)

    def update(self, db: Session, id: int, obj_in: AuditLogUpdate):
        """
        Update an existing AuditLog using validated input data.

        Args:
            db: Active database session.
            id: Primary key of the record to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated AuditLog instance.
        """
        db_obj = crud_audit_log.get(db, id)
        return crud_audit_log.update(db, db_obj, obj_in)

    def delete(self, db: Session, id: int):
        """
        Delete a AuditLog by ID.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        return crud_audit_log.delete(db, id)

audit_log_service = AuditLogService()
