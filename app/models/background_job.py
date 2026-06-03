# ER-ServiceDesk/app/models/background_job.py
# ORM model for tracking asynchronous background jobs
#
# The BackgroundJob model stores metadata about queued or processed
# background tasks within the ER‑ServiceDesk system. This includes job
# type, execution status, payload data, and timestamps for auditing and
# monitoring worker activity.

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# BackgroundJob Model
# ---------------------------------------------------------------------------
class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Type of job (e.g., "send_email", "generate_report")
    job_type = Column(String, nullable=False)

    # Current status (e.g., "queued", "running", "completed", "failed")
    status = Column(String, nullable=False)

    # Optional JSON/text payload with job parameters
    payload = Column(Text, nullable=True)

    # Timestamp when the job was created
    created_at = Column(DateTime, default=datetime.utcnow)

    # Timestamp updated automatically on modification
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
