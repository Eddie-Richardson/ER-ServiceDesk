# ER-ServiceDesk/app/models/message_template.py
# ORM model for reusable message templates
#
# The MessageTemplate model stores predefined email or notification
# templates used throughout the ER‑ServiceDesk system. These templates
# allow administrators to manage standardized communication formats
# without modifying application code.

from sqlalchemy import Column, Integer, String, Text

from app.db.base import Base

# ---------------------------------------------------------------------------
# MessageTemplate Model
# ---------------------------------------------------------------------------
class MessageTemplate(Base):
    __tablename__ = "message_templates"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Unique template name (e.g., "ticket_created", "password_reset")
    name = Column(String, unique=True, nullable=False)

    # Optional subject line for email-based templates
    subject = Column(String, nullable=True)

    # Template body (supports full text, placeholders, etc.)
    body = Column(Text, nullable=False)
