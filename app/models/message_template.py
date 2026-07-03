# ER-ServiceDesk/app/models/message_template.py
# ORM model for a reusable template for outbound emails/notifications
"""
ORM model for a reusable template for outbound emails/notifications.
"""

from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class MessageTemplate(Base):
    """
    Represents a predefined subject/body pair used for standardized customer communication.

    Attributes:
        id: Primary key.
        name: Unique template identifier (e.g. 'ticket_created').
        subject: Email subject line for this template.
        body: Template body, may contain placeholders.
    """
    __tablename__ = "message_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
