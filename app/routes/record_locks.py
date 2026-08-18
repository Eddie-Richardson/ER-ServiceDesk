# ER-ServiceDesk/app/routes/record_locks.py
# API routes for check-out style record locking.
"""
REST endpoints for acquiring/releasing locks on a record being edited.

Generic across every entity type in the app (tickets, customers,
assets, etc.) rather than one route pair per resource -- see
RecordLock's docstring for why. Requires only a normal authenticated
session, not any specific permission -- anyone who can edit a given
record type on their own already has whatever permission that requires;
this layer is purely about preventing two people from editing the same
one at once, not an additional access restriction.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.record_lock import LockRequest, LockResult
from app.services.record_lock_service import record_lock_service

router = APIRouter(prefix="/locks", tags=["locks"], dependencies=[Depends(get_current_user)])


@router.post("/acquire", response_model=LockResult)
def acquire_lock(
    request: LockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns:
        The new (or refreshed) lock.

    Raises:
        HTTPException: 409 if someone else currently holds a non-stale
            lock on this record.
    """
    return record_lock_service.acquire(db, request.entity_type, request.entity_id, current_user.id)


@router.post("/release")
def release_lock(
    request: LockRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """A safe no-op if the record isn't locked, or is locked by someone else."""
    record_lock_service.release(db, request.entity_type, request.entity_id, current_user.id)
    return {"released": True}
