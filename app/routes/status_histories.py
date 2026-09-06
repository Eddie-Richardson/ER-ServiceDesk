# ER-ServiceDesk/app/routes/status_histories.py
"""
Read-only REST endpoint for a ticket's status change history.

Deliberately GET-only -- StatusHistory entries are only ever created
internally by ticket_service.py, whenever a ticket's status_id
genuinely changes. There's no create/update/delete route here at all:
an audit trail a regular user could freely rewrite or erase through
the API wouldn't be a trustworthy audit trail, which defeats the
entire point of building this.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import get_current_user
from app.services.status_history_service import status_history_service
from app.schemas.status_history import StatusHistory

router = APIRouter(prefix="/status_histories", tags=["status_histories"], dependencies=[Depends(get_current_user)])

@router.get("/", response_model=list[StatusHistory])
def list_status_histories(db: Session = Depends(get_db)):
    """
    Every status change ever recorded, across every ticket. Visible to
    anyone with an active session -- the desktop client filters this
    down to one ticket's own history client-side (see
    api_client.list_status_history_for_ticket()), matching the same
    pattern already used for a ticket's Notes/Message timeline.
    """
    return status_history_service.get_multi(db)

@router.get("/{id}", response_model=StatusHistory)
def get_status_history(id: int, db: Session = Depends(get_db)):
    return status_history_service.get(db, id)
