# ER-ServiceDesk/app/schemas/note_template.py
"""
Request/response schemas for a reusable template for ticket notes.
"""

from pydantic import BaseModel, ConfigDict

class NoteTemplateBase(BaseModel):
    """Shared fields for NoteTemplate across create/read/update."""
    name: str
    body: str

class NoteTemplateCreate(NoteTemplateBase):
    """Schema for creating a new NoteTemplate record (client -> server)."""
    pass

class NoteTemplateUpdate(BaseModel):
    """Schema for partially updating an existing NoteTemplate record. All fields optional."""
    name: str | None = None
    body: str | None = None

class NoteTemplate(NoteTemplateBase):
    """Schema returned to the client for a NoteTemplate record (server -> client)."""
    id: int
    model_config = ConfigDict(from_attributes=True)
