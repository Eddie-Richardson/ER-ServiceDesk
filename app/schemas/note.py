# ER-ServiceDesk/app/schemas/note.py
"""
Pydantic schemas for Note -- a ticket's full note/conversation
history, covering internal notes and customer-facing email exchange
in one system rather than two separate ones.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class NoteBase(BaseModel):
    """Shared fields for Note across create/read."""
    ticket_id: int
    customer_id: int | None = None
    user_id: int | None = None
    direction: str  # 'internal', 'outbound', or 'inbound'
    content: str

class NoteCreate(NoteBase):
    """Schema for creating a new Note record (client -> server)."""
    pass

class NoteUpdate(BaseModel):
    """
    Schema for editing an existing Note's content. Deliberately
    just content -- direction/email_status/etc. are a record of what
    happened at creation time, not something an edit should be able
    to change (there's no way to un-send an email a customer already
    received by flipping a field).
    """
    content: str

class Note(NoteBase):
    """Schema returned to the client for a Note record (server -> client)."""
    id: int
    email_status: str | None = None
    author_name: str | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
