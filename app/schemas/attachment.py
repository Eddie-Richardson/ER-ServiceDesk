# ER-ServiceDesk/app/schemas/attachment.py
# Pydantic schemas for Attachment entities used to validate and structure a file uploaded and linked to a support ticket
"""
Pydantic schemas for Attachment entities used to validate and structure a file uploaded and linked to a support ticket.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class AttachmentBase(BaseModel):
    """Shared fields for Attachment across create/read/update."""
    ticket_id: int
    file_path: str
    file_name: str

class AttachmentCreate(AttachmentBase):
    """Schema for creating a new Attachment record (client -> server)."""
    pass

class AttachmentUpdate(BaseModel):
    """Schema for partially updating an existing Attachment record. All fields optional."""
    ticket_id: int | None = None
    file_path: str | None = None
    file_name: str | None = None

class Attachment(AttachmentBase):
    """Schema returned to the client for a Attachment record (server -> client)."""
    id: int
    uploaded_at: datetime
    model_config = ConfigDict(from_attributes=True)
