# ER-ServiceDesk/app/routes/audit_logs.py
# API routes for AuditLog operations.
#
# Exposes REST endpoints for interacting with AuditLog records.
# Uses the service layer to perform business logic.
# Defines request/response schemas and HTTP method handlers.

# ---------------------------------------------------------------------------
# Route Handlers
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.audit_log_service import audit_log_service
from app.schemas.audit_log import AuditLog, AuditLogCreate, AuditLogUpdate

router = APIRouter(prefix="/audit_logs", tags=["audit_logs"])

@router.get("/", response_model=list[AuditLog])
def list_audit_logs(db: Session = Depends(get_db)):
    """
    Returns a list of AuditLog records.
    """
    return audit_log_service.get_multi(db)

@router.get("/{id}", response_model=AuditLog)
def get_audit_log(id: int, db: Session = Depends(get_db)):
    """
    Returns a single AuditLog record by ID.
    """
    return audit_log_service.get(db, id)

@router.post("/", response_model=AuditLog)
def create_audit_log(obj_in: AuditLogCreate, db: Session = Depends(get_db)):
    """
    Creates a new AuditLog record.
    """
    return audit_log_service.create(db, obj_in)

@router.put("/{id}", response_model=AuditLog)
def update_audit_log(id: int, obj_in: AuditLogUpdate, db: Session = Depends(get_db)):
    """
    Updates an existing AuditLog record.
    """
    return audit_log_service.update(db, id, obj_in)

@router.delete("/{id}")
def delete_audit_log(id: int, db: Session = Depends(get_db)):
    """
    Deletes an AuditLog record by ID.
    """
    return audit_log_service.delete(db, id)
