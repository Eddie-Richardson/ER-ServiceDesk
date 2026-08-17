# ER-ServiceDesk/app/services/audit_log_service.py
# Service layer for AuditLog -- read/list, plus a reusable log() helper for other services.
"""
Business logic for the security/compliance audit trail.

No update()/delete() here -- matches the CRUD layer below this (see
crud/audit_log.py): an audit trail that could be rewritten after the
fact isn't trustworthy.

log() is the real entry point other services actually use -- a small,
reusable helper so instrumenting a new action elsewhere in the app is
a one-line call, not hand-rolled AuditLogCreate construction at every
call site. Deliberately swallows its own failures (logged, not
raised) -- a transient audit-log write failure should never be able to
break the real operation it's trying to record (e.g. a ticket
genuinely being created shouldn't fail just because the audit write
that describes it had a hiccup).
"""

import logging

from sqlalchemy.orm import Session
from app.crud.audit_log import crud_audit_log
from app.schemas.audit_log import AuditLogCreate

logger = logging.getLogger(__name__)


class AuditLogService:
    """Read/list access to the audit trail, plus the log() helper other services call to write to it."""

    def get(self, db: Session, id: int):
        return crud_audit_log.get(db, id)

    def get_multi(self, db: Session, skip: int = 0, limit: int = 500, user_id: int | None = None, entity_type: str | None = None, entity_id: int | None = None):
        return crud_audit_log.get_multi(db, skip, limit, user_id, entity_type, entity_id)

    def log(
        self,
        db: Session,
        action: str,
        entity_type: str,
        entity_id: int,
        user_id: int | None = None,
        details: str | None = None,
    ) -> None:
        """
        The real entry point every other service actually calls -- e.g.
        audit_log_service.log(db, "ticket_created", "ticket", ticket.id, user_id=current_user_id).

        Args:
            action: Short label for the action, e.g. "login_success",
                "ticket_created", "user_deleted".
            entity_type: The kind of entity affected, e.g. "ticket",
                "user", "customer".
            entity_id: The specific entity instance's ID.
            user_id: The user who performed the action, if any --
                omitted (None) for a genuinely system-initiated action
                with no specific user behind it.
            details: Optional free-text context, e.g. "priority
                changed from Normal to High".
        """
        try:
            crud_audit_log.create(db, AuditLogCreate(
                user_id=user_id,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            ))
        except Exception:
            logger.exception(
                "Failed to write audit log entry: action=%s entity_type=%s entity_id=%s user_id=%s",
                action, entity_type, entity_id, user_id,
            )

audit_log_service = AuditLogService()
