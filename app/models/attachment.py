# ER-ServiceDesk/app/models/attachment.py
# ORM model for a file uploaded and linked to a support ticket
"""
ORM model for a file uploaded and linked to a support ticket.
"""

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Attachment(Base):
    """
    Represents an uploaded file attached to a ticket (e.g. photos, diagnostic reports, receipts).

    Attributes:
        id: Primary key.
        ticket_id: The ticket this file is attached to.
        file_path: Storage path of the uploaded file.
        file_name: Original filename as uploaded.
        uploaded_at: Timestamp the file was uploaded.
    """
    __tablename__ = "attachments"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    file_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket")
