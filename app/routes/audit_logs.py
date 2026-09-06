# ER-ServiceDesk/app/routes/audit_logs.py
"""
Read-only REST endpoint for the security/compliance audit trail.

Deliberately GET-only -- entries are only ever written internally by
other services (via audit_log_service.log()), never directly through
the API. An audit trail a user could rewrite or erase through a route
wouldn't be trustworthy, even for a superuser -- a compromised admin
account could otherwise just cover its own tracks.

Superuser-only, matching the sensitive nature of this data -- this is
a full activity record across every user, not something a regular
tech should be able to browse.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.audit_log_service import audit_log_service
from app.schemas.audit_log import AuditLog

router = APIRouter(prefix="/audit_logs", tags=["audit_logs"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[AuditLog])
def list_audit_logs(
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: int | None = None,
    db: Session = Depends(get_db),
):
    """
    Most recent first, optionally filtered to a specific user and/or
    entity -- lets an admin pull up "everything this one user has
    done," "everything that's happened to tickets," or "this one
    ticket's full history" without fetching the entire table.

    Args:
        user_id: If given, only entries performed by this user.
        entity_type: If given, only entries for this kind of entity
            (e.g. "ticket", "user", "customer").
        entity_id: If given (along with entity_type), only entries for
            that one specific entity instance.
    """
    return audit_log_service.get_multi(db, user_id=user_id, entity_type=entity_type, entity_id=entity_id)

@router.get("/{id}", response_model=AuditLog)
def get_audit_log(id: int, db: Session = Depends(get_db)):
    return audit_log_service.get(db, id)
