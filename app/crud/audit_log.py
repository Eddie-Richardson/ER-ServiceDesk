# ER-ServiceDesk/app/crud/audit_log.py
"""
Database access layer for the security/compliance audit trail.

Deliberately no update() or delete() -- this is meant to be an
immutable record. Even a superuser can't edit or erase an entry
through this layer, since an audit trail a compromised admin account
could rewrite to cover its own tracks isn't a trustworthy audit trail
at all.
"""

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate

class AuditLogCRUD:
    """Direct database access for AuditLog records -- read and create only."""

    def get(self, db: Session, id: int) -> AuditLog | None:
        return db.query(AuditLog).filter(AuditLog.id == id).first()

    def get_multi(self, db: Session, skip: int = 0, limit: int = 500, user_id: int | None = None, entity_type: str | None = None, entity_id: int | None = None):
        """
        Fetch multiple AuditLog records with simple offset pagination,
        newest first, optionally filtered.

        Args:
            limit: Defaults higher than most other lookups (500, not
                100) since this is meant to be reviewed as a real log,
                not paged through a handful at a time.
            user_id: If given, only entries performed by this user.
            entity_type: If given, only entries for this kind of
                entity (e.g. "ticket", "user").
            entity_id: If given (along with entity_type), only entries
                for that one specific entity instance -- e.g. a single
                ticket's own history, not every ticket's entries.
        """
        query = db.query(AuditLog)
        if user_id is not None:
            query = query.filter(AuditLog.user_id == user_id)
        if entity_type is not None:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id is not None:
            query = query.filter(AuditLog.entity_id == entity_id)
        return query.order_by(AuditLog.created_at.desc()).offset(skip).limit(limit).all()

    def create(self, db: Session, obj_in: AuditLogCreate) -> AuditLog:
        """Only ever called internally by other services logging a real action -- never directly from a route."""
        obj = AuditLog(**obj_in.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

crud_audit_log = AuditLogCRUD()
