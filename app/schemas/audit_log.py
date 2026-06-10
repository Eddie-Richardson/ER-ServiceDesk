# ER-ServiceDesk/app/schemas/audit_log.py
# Pydantic schemas for audit log entries used to track user actions
# and system events within the ER‑ServiceDesk application.
#
# These schemas define the structure for creating, updating, and
# returning audit log records. Audit logs are essential for
# security reviews, compliance, and debugging.

from datetime import datetime
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class AuditLogBase(BaseModel):
    user_id: int | None = None
    action: str
    details: str | None = None
    entity_type: str
    entity_id: int


# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class AuditLogCreate(AuditLogBase):
    pass


# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class AuditLogUpdate(BaseModel):
    user_id: int | None = None
    action: str | None = None
    details: str | None = None
    entity_type: str | None = None
    entity_id: int | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class AuditLog(AuditLogBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
