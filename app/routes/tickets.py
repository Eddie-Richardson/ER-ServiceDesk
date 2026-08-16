# ER-ServiceDesk/app/routes/tickets.py
# API routes for Ticket operations.
"""
REST endpoints for a support/repair job tracked from intake to completion.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_permission, get_current_user
from app.models.user import User
from app.services.ticket_service import ticket_service
from app.services.audit_log_service import audit_log_service
from app.services.waiver_service import waiver_service
from app.schemas.ticket import Ticket, TicketCreate, TicketUpdate
from app.schemas.audit_log import AuditLog

router = APIRouter(prefix="/tickets", tags=["tickets"], dependencies=[Depends(require_permission("tickets.manage"))])

@router.get("/", response_model=list[Ticket])
def list_tickets(db: Session = Depends(get_db)):
    """
    List a support/repair job tracked from intake to completion, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of Ticket records.
    """
    return ticket_service.get_multi(db)

@router.get("/{id}", response_model=Ticket)
def get_ticket(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single Ticket record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching Ticket record.
    """
    return ticket_service.get(db, id)

@router.post("/", response_model=Ticket)
def create_ticket(
    obj_in: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new Ticket record. Also records its initial status as
    the first StatusHistory entry (see ticket_service.create()).

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.
        current_user: The authenticated user making this request --
            recorded as who set the ticket's initial status.

    Returns:
        The newly created Ticket record.
    """
    return ticket_service.create(db, obj_in, current_user.id)

@router.put("/{id}", response_model=Ticket)
def update_ticket(
    id: int,
    obj_in: TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update an existing Ticket record. If status_id actually changes,
    also records a StatusHistory entry for it (see
    ticket_service.update()).

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.
        current_user: The authenticated user making this request --
            recorded as who made the change, if status_id changes.

    Returns:
        The updated Ticket record.
    """
    return ticket_service.update(db, id, obj_in, current_user.id)

@router.get("/{id}/audit-log", response_model=list[AuditLog])
def get_ticket_audit_log(id: int, db: Session = Depends(get_db)):
    """
    List this ticket's own audit trail entries (created, updated, an
    inbound email matching, an outbound notification sending or
    failing), most recent first.

    Deliberately gated at the same tickets.manage level as every other
    route in this file, not superuser-only like the general
    /audit_logs/ endpoint -- viewing one ticket's own history is
    reasonable for any tech with access to that ticket, unlike
    browsing the full audit log across every user and entity.

    Args:
        id: The ticket to fetch audit history for.
        db: Injected database session.

    Returns:
        A list of AuditLog records for this ticket.
    """
    return audit_log_service.get_multi(db, entity_type="ticket", entity_id=id)


@router.post("/{id}/send-waiver", response_model=Ticket)
def send_waiver(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    Emails the liability waiver to this ticket's customer, and records
    when it was sent. Email-only -- there's no print/signature path.
    The customer's "I AGREE" reply, if any, comes back as a normal
    Note on the ticket through the existing inbound-email system.

    Args:
        id: The ticket to send the waiver for.
        db: Injected database session.
        current_user: The user sending this -- recorded in the audit trail.

    Returns:
        The updated Ticket, with waiver_sent_at set.
    """
    return waiver_service.send(db, id, current_user.id)
