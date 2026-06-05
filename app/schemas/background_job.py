# ER-ServiceDesk/app/schemas/background_job.py
# Pydantic schemas for BackgroundJob entities used to validate and
# structure data exchanged between the client and server.
#
# These schemas define the fields required for creating, updating,
# and returning background job records within the ER‑ServiceDesk system.

from datetime import datetime
from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Base Schema (shared fields)
# ---------------------------------------------------------------------------
class BackgroundJobBase(BaseModel):
    job_type: str
    status: str
    payload: str | None = None


# ---------------------------------------------------------------------------
# Create Schema (client → server)
# ---------------------------------------------------------------------------
class BackgroundJobCreate(BackgroundJobBase):
    pass


# ---------------------------------------------------------------------------
# Update Schema (partial updates allowed)
# ---------------------------------------------------------------------------
class BackgroundJobUpdate(BaseModel):
    id: int | None = None
    job_type: str | None = None
    status: str | None = None
    payload: str | None = None
    updated_at: datetime | None = None


# ---------------------------------------------------------------------------
# Response Schema (server → client)
# ---------------------------------------------------------------------------
class BackgroundJob(BackgroundJobBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True
