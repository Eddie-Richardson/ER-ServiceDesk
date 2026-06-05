# ER-ServiceDesk/app/schemas/message.py
# Pydantic schemas for Message entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning message records within the ER‑ServiceDesk system.
# They support ticket communication workflows, including inbound
# customer replies and outbound agent or system messages.

from datetime import datetime
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class MessageBase(BaseModel):
    ticket_id: int
    customer_id: int
    direction: str
    content: str

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class MessageCreate(MessageBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class MessageUpdate(BaseModel):
    ticket_id: int | None = None
    customer_id: int | None = None
    direction: str | None = None
    content: str | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class Message(MessageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True