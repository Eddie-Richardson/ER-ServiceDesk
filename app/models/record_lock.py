# ER-ServiceDesk/app/models/record_lock.py
# ORM model for a generic check-out style edit lock

"""
ORM model for a check-out style lock on a record being edited.

One generic table covers every editable entity type in the app
(tickets, customers, devices, assets, parts, users, roles, and every
lookup table) rather than a separate lock column per table -- the same
"one reusable thing instead of N near-identical things" reasoning
already used for the lookup-table CRUD pattern.

entity_type is a short string identifying which kind of record this is
(e.g. "ticket", "customer", "asset"); entity_id is that record's own
primary key. Together they're unique -- only one active lock per record
at a time.
"""

from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class RecordLock(Base):
    """
    Represents an active check-out lock on a record being edited.

    Attributes:
        id: Primary key.
        entity_type: Short identifier for the kind of record locked,
            e.g. "ticket", "customer", "asset".
        entity_id: The primary key of the locked record within its own table.
        locked_by_user_id: The user currently holding the lock.
        locked_at: When the lock was acquired. Used to determine
            whether a lock has gone stale (see RecordLockService).
    """
    __tablename__ = "record_locks"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_record_lock_entity"),
    )

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False, index=True)
    entity_id = Column(Integer, nullable=False)
    locked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    locked_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    locked_by = relationship("User")
