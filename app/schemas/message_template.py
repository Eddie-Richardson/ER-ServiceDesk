# ER-ServiceDesk/app/schemas/message_template.py
# Pydantic schemas for MessageTemplate entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning reusable message template records within the
# ER‑ServiceDesk system. They support standardized outbound
# communication formats for ticket and notification workflows.

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class MessageTemplateBase(BaseModel):
    name: str
    subject: str
    body: str

# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class MessageTemplateCreate(MessageTemplateBase):
    pass

# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class MessageTemplateUpdate(BaseModel):
    name: str | None = None
    subject: str | None = None
    body: str | None = None

# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class MessageTemplate(MessageTemplateBase):
    id: int

    class Config:
        orm_mode = True