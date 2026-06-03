# ER-ServiceDesk/app/models/audit_log.py
# ORM model for recording user actions and system events
#
# The AuditLog model stores a historical record of actions performed within
# the ER‑ServiceDesk application. This includes user‑initiated actions,
# automated system events, and administrative operations. Audit logs are
# essential for security reviews, compliance, and debugging.

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from datetime import datetime

from app.db.base import Base

# ---------------------------------------------------------------------------
# AuditLog Model
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_logs"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Optional reference to the user who performed the action
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    # Short description of the action (e.g., "login", "update_ticket")
    action = Column(String, nullable=False)

    # Additional details or context about the action
    details = Column(Text, nullable=True)

    # Timestamp of when the log entry was created
    created_at = Column(DateTime, default=datetime.utcnow)
