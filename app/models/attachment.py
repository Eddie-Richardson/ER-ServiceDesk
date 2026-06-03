# ER-ServiceDesk/app/models/attachment.py
# ORM model for storing file attachments linked to support tickets
#
# The Attachment model represents uploaded files associated with tickets
# in the ER‑ServiceDesk system. Each attachment stores metadata such as
# file name, storage path, and upload timestamp. Attachments are linked
# to tickets through a foreign key relationship.

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# Attachment Model
# ---------------------------------------------------------------------------
class Attachment(Base):
    __tablename__ = "attachments"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Foreign key linking the attachment to a ticket
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)

    # File storage path (e.g., "uploads/2025/01/file123.pdf")
    file_path = Column(String, nullable=False)

    # Original file name uploaded by the user
    file_name = Column(String, nullable=False)

    # Timestamp when the file was uploaded
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship back to the Ticket model
    ticket = relationship("Ticket")
