# ER-ServiceDesk/app/schemas/note.py
# Pydantic schemas for Note entities used to validate and structure an internal or customer-visible annotation on a ticket
"""
Pydantic schemas for Note entities used to validate and structure an internal or customer-visible annotation on a ticket.
"""

from datetime import datetime
from pydantic import BaseModel

class NoteBase(BaseModel):
    """Shared fields for Note across create/read/update."""
    ticket_id: int
    user_id: int
    is_public: bool
    content: str

class NoteCreate(NoteBase):
    """Schema for creating a new Note record (client -> server)."""
    pass

class NoteUpdate(BaseModel):
    """Schema for partially updating an existing Note record. All fields optional."""
    ticket_id: int | None = None
    user_id: int | None = None
    is_public: bool | None = None
    content: str | None = None
    updated_at: datetime | None = None

class Note(NoteBase):
    """Schema returned to the client for a Note record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    class Config:
        orm_mode = True
