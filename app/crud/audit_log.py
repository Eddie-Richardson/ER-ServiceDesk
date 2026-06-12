# ER-ServiceDesk/app/crud/audit_log.py
# CRUD operations for the AuditLog model.
#
# Provides database access for creating, reading, updating, and deleting AuditLog records.
# Used by the service layer to perform data operations.
# Contains no business logic; only direct database interaction.

# ---------------------------------------------------------------------------
# CRUD Operations
# ---------------------------------------------------------------------------

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate, AuditLogUpdate

class AuditLogCRUD:
    # Retrieves a single AuditLog by ID.
    def get(self, db: Session, id: int) -> AuditLog | None:
        """
        Returns a single AuditLog instance matching the given ID.
        """
        return db.query(AuditLog).filter(AuditLog.id == id).first()

    # Retrieves multiple AuditLog records.
    def get_multi(self, db: Session, skip: int = 0, limit: int = 100):
        """
        Returns a list of AuditLog records with pagination support.
        """
        return db.query(AuditLog).offset(skip).limit(limit).all()

    # Creates a new AuditLog record.
    def create(self, db: Session, obj_in: AuditLogCreate) -> AuditLog:
        """
        Creates a new AuditLog using the provided input schema.
        """
        obj = AuditLog(**obj_in.dict())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    # Updates an existing AuditLog record.
    def update(self, db: Session, db_obj: AuditLog, obj_in: AuditLogUpdate) -> AuditLog:
        """
        Updates the given AuditLog instance with new values.
        """
        for field, value in obj_in.dict(exclude_unset=True).items():
            setattr(db_obj, field, value)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    # Deletes an AuditLog record by ID.
    def delete(self, db: Session, id: int) -> None:
        """
        Deletes the AuditLog instance matching the given ID.
        """
        obj = db.query(AuditLog).filter(AuditLog.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()

crud_audit_log = AuditLogCRUD()
