# ER-ServiceDesk/app/schemas/background_job.py
"""
Request/response schemas for an asynchronous job tracked for the RQ
worker system.
"""

from datetime import datetime
from pydantic import BaseModel, ConfigDict

class BackgroundJobBase(BaseModel):
    """Shared fields for BackgroundJob across create/read/update."""
    job_type: str
    status: str
    payload: str | None = None

class BackgroundJobCreate(BackgroundJobBase):
    """Schema for creating a new BackgroundJob record (client -> server)."""
    pass

class BackgroundJobUpdate(BaseModel):
    """Schema for partially updating an existing BackgroundJob record. All fields optional."""
    job_type: str | None = None
    status: str | None = None
    payload: str | None = None
    updated_at: datetime | None = None

class BackgroundJob(BackgroundJobBase):
    """Schema returned to the client for a BackgroundJob record (server -> client)."""
    id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)
