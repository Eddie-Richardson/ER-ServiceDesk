# ER-ServiceDesk/app/models/message_template.py
"""
ORM model for a reusable template for ticket notes.
"""

from sqlalchemy import Column, Integer, String, Text
from app.db.base import Base

class MessageTemplate(Base):
    """
    Represents a predefined body used for standardized ticket notes.

    Attributes:
        name: A short, admin-chosen label for the tech's own reference when picking a template -- not matched against anything in code.
    """
    __tablename__ = "message_templates"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    body = Column(Text, nullable=False)
