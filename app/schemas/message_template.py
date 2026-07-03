# ER-ServiceDesk/app/schemas/message_template.py
# Pydantic schemas for MessageTemplate entities used to validate and structure a reusable template for outbound emails/notifications
"""
Pydantic schemas for MessageTemplate entities used to validate and structure a reusable template for outbound emails/notifications.
"""

from pydantic import BaseModel

class MessageTemplateBase(BaseModel):
    """Shared fields for MessageTemplate across create/read/update."""
    name: str
    subject: str
    body: str

class MessageTemplateCreate(MessageTemplateBase):
    """Schema for creating a new MessageTemplate record (client -> server)."""
    pass

class MessageTemplateUpdate(BaseModel):
    """Schema for partially updating an existing MessageTemplate record. All fields optional."""
    name: str | None = None
    subject: str | None = None
    body: str | None = None

class MessageTemplate(MessageTemplateBase):
    """Schema returned to the client for a MessageTemplate record (server -> client)."""
    id: int
    class Config:
        orm_mode = True
