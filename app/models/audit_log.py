# ER-ServiceDesk/app/models/audit_log.py
# ORM model for a record of a user action or system event, for security review and compliance
"""
ORM model for a record of a user action or system event, for security review and compliance.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class AuditLog(Base):
    """
    Represents a single logged action taken by a user or the system, tied to the entity it affected.

    Attributes:
        user_id: The user who performed the action, if any -- null
            for a genuinely system-initiated action with no specific
            user behind it.
        action: Short label for the action (e.g. 'login', 'update_ticket').
        entity_type: The kind of entity affected (e.g. 'ticket', 'user').
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
    user = relationship("User")

    @property
    def user_name(self) -> str | None:
        """
        Returns:
            The acting user's display name, or None for a genuinely
            system-initiated action with no user_id at all.
            Denormalized so the API response can include it directly
            (see schemas/audit_log.py), matching the same reasoning as
            StatusHistory.changed_by_name -- avoids a separate
            /users/ lookup just to show who did something.
        """
        return self.user.full_name if self.user else None
