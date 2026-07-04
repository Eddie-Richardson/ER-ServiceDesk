# ER-ServiceDesk/app/routes/audit_logs.py
# API routes for AuditLog operations.
"""
REST endpoints for a record of a user action or system event, for security review and compliance.

Thin HTTP layer: validates the request via the schema layer and delegates
all real work to the service layer.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.dependencies import require_superuser
from app.services.audit_log_service import audit_log_service
from app.schemas.audit_log import AuditLog, AuditLogCreate, AuditLogUpdate

router = APIRouter(prefix="/audit_logs", tags=["audit_logs"], dependencies=[Depends(require_superuser)])

@router.get("/", response_model=list[AuditLog])
def list_audit_logs(db: Session = Depends(get_db)):
    """
    List a record of a user action or system event, for security review and compliance, paginated.

    Args:
        db: Injected database session.

    Returns:
        A list of AuditLog records.
    """
    return audit_log_service.get_multi(db)

@router.get("/{id}", response_model=AuditLog)
def get_audit_log(id: int, db: Session = Depends(get_db)):
    """
    Fetch a single AuditLog record by ID.

    Args:
        id: Primary key of the record to fetch.
        db: Injected database session.

    Returns:
        The matching AuditLog record.
    """
    return audit_log_service.get(db, id)

@router.post("/", response_model=AuditLog)
def create_audit_log(obj_in: AuditLogCreate, db: Session = Depends(get_db)):
    """
    Create a new AuditLog record.

    Args:
        obj_in: Validated request body for the new record.
        db: Injected database session.

    Returns:
        The newly created AuditLog record.
    """
    return audit_log_service.create(db, obj_in)

@router.put("/{id}", response_model=AuditLog)
def update_audit_log(id: int, obj_in: AuditLogUpdate, db: Session = Depends(get_db)):
    """
    Update an existing AuditLog record.

    Args:
        id: Primary key of the record to update.
        obj_in: Fields to change; unset fields are left untouched.
        db: Injected database session.

    Returns:
        The updated AuditLog record.
    """
    return audit_log_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_audit_log(id: int, db: Session = Depends(get_db)):
    """
    Delete a AuditLog record by ID.

    Args:
        id: Primary key of the record to delete.
        db: Injected database session.
    """
    return audit_log_service.delete(db, id)
