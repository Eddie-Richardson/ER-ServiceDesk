# ER-ServiceDesk/app/models/background_job.py
# ORM model for an asynchronous job tracked for the RQ worker system
"""
ORM model for an asynchronous job tracked for the RQ worker system.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from datetime import datetime, UTC
from app.db.base import Base

class BackgroundJob(Base):
    """
    Represents a queued or processed background task, along with its status and payload.

    Attributes:
        job_type: The kind of job (e.g. 'send_email', 'generate_report').
        status: Current job status (e.g. 'queued', 'running', 'completed', 'failed').
    """
    __tablename__ = "background_jobs"
    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(String, nullable=False)
    status = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
