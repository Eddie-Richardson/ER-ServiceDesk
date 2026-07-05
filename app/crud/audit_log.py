# ER-ServiceDesk/app/crud/audit_log.py
# CRUD operations for the AuditLog model.
"""
Database access layer for a record of a user action or system event, for security review and compliance.

Talks directly to the database via SQLAlchemy. Contains no business logic --
callers (the service layer) are responsible for that. Kept intentionally
"dumb" so it stays simple to test and reuse.
"""

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate

class AuditLogCRUD:
    """Direct database access for AuditLog records."""

    def get(self, db: Session, id: int) -> AuditLog | None:
        """
        Fetch a single AuditLog by primary key.

        Args:
            db: Active database session.
            id: Primary key of the record to fetch.

        Returns:
            The matching AuditLog instance, or None if no record exists.
        """
        return db.query(AuditLog).filter(AuditLog.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Fetch multiple AuditLog records with simple offset pagination.

        Args:
            db: Active database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            A list of AuditLog instances.
        """
        return db.query(AuditLog).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AuditLogCreate) -> AuditLog:
        """
        Insert a new AuditLog record.

        Args:
            db: Active database session.
            obj_in: Validated input data for the new record.

        Returns:
            The newly created, refreshed AuditLog instance.
        """
        obj = AuditLog(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    def update(self, db: Session, db_obj: AuditLog, obj_in: AuditLogUpdate) -> AuditLog:
        """
        Apply a partial update to an existing AuditLog record.

        Args:
            db: Active database session.
            db_obj: The existing AuditLog instance to update.
            obj_in: Fields to change; unset fields are left untouched.

        Returns:
            The updated, refreshed AuditLog instance.
        """
        for field, value in obj_in.model_dump(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def delete(self, db: Session, id: int) -> None:
        """
        Delete a AuditLog record by primary key, if it exists.

        Args:
            db: Active database session.
            id: Primary key of the record to delete.
        """
        obj = db.query(AuditLog).filter(AuditLog.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_audit_log = AuditLogCRUD()
