# ER-ServiceDesk/app/schemas/audit_log.py
"""
Request/response schemas for a record of a user action or system event,
for security review and compliance.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AuditLogBase(BaseModel):
    """Shared fields for AuditLog across create/read/update."""
    user_id: int | None = None
    action: str
    details: str | None = None
    entity_type: str
    entity_id: int

class AuditLogCreate(AuditLogBase):
    """Schema for creating a new AuditLog record (client -> server)."""
    pass

class AuditLog(AuditLogBase):
    """Schema returned to the client for a AuditLog record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    user_name: str | None = None
    model_config = ConfigDict(from_attributes=True)
