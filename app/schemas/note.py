# ER-ServiceDesk/app/schemas/notes.py
# Pydantic schemas for Note entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning note records within the ER‑ServiceDesk system.
# They support internal and customer-visible annotations on
# support tickets, enabling private agent collaboration and
# public customer updates.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class NoteBase(BaseModel):
    ticket_id: int
    user_id: int
    is_public: bool
    content: str

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class NoteCreate(NoteBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class NoteUpdate(BaseModel):
    ticket_id: int | None = None
    user_id: int | None = None
    is_public: bool | None = None
    content: str | None = None
    updated_at: datetime | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Note(NoteBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
