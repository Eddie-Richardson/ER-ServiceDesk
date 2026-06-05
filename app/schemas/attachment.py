# ER-ServiceDesk/app/schemas/attachment.py
# Pydantic schemas for file attachments linked to support tickets
#
# The Attachment schemas define the data structures used for creating,
# updating, and returning attachment records in the ER‑ServiceDesk API.
# These schemas mirror the Attachment ORM model, which represents uploaded
# files associated with tickets, including metadata such as file name,
# storage path, and upload timestamp.

from datetime import datetime
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class AttachmentBase(BaseModel):
    ticket_id: int
    file_path: str
    file_name: str


# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class AttachmentCreate(AttachmentBase):
    pass


# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class AttachmentUpdate(BaseModel):
    ticket_id: int | None = None
    file_path: str | None = None
    file_name: str | None = None


# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Attachment(AttachmentBase):
    id: int
    uploaded_at: datetime

    class Config:
        orm_mode = True
