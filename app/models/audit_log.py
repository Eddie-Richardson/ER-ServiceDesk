# ER-ServiceDesk/app/models/audit_log.py
# ORM model for a record of a user action or system event, for security review and compliance
"""
ORM model for a record of a user action or system event, for security review and compliance.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime, UTC
from app.db.base import Base

class AuditLog(Base):
    """
    Represents a single logged action taken by a user or the system, tied to the entity it affected.

    Attributes:
        id: Primary key.
        user_id: The user who performed the action, if any.
        action: Short label for the action (e.g. 'login', 'update_ticket').
        details: Additional free-text context about the action.
        entity_type: The kind of entity affected (e.g. 'ticket', 'user').
        entity_id: The ID of the specific entity instance affected.
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
