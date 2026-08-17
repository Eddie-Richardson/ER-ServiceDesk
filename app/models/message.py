# ER-ServiceDesk/app/models/message.py
# ORM model for a ticket's full note/conversation history -- internal notes and customer-facing email exchange, unified.
"""
ORM model for a ticket's full note/conversation history -- internal
notes and customer-facing email exchange, unified into one system
rather than two separate ones.
"""

from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime, String
from sqlalchemy.orm import relationship
from datetime import datetime, UTC
from app.db.base import Base

class Message(Base):
    """
    A single entry in a ticket's note/conversation history.

    Attributes:
        customer_id: Nullable -- an internal-only entry has no
            customer involved at all.
        user_id: Nullable -- an inbound entry (the customer's own
            reply) has no staff author; it's attributed to
            customer_id instead.
        direction: 'internal' (staff-only, never emailed), 'outbound'
            (staff-authored, sent to the customer), or 'inbound' (the
            customer's own reply, created by the inbound-email polling
            worker -- see app/workers/tasks.py's poll_inbound_email).
        email_status: For outbound entries only -- 'sent' or 'failed'.
            Null for internal/inbound, where it doesn't apply. A tech
            seeing 'failed' here knows the customer was NOT notified
            and should retry or call them directly.
        updated_at: Timestamp of the last edit -- see message_service.py
            for who's allowed to make one.
    """
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    direction = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    email_status = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC), nullable=False)
    ticket = relationship("Ticket")
    customer = relationship("Customer")
    user = relationship("User")

    @property
    def author_name(self):
        """
        Display name for whoever authored this entry -- the staff
        member for internal/outbound, the customer themselves for
        inbound. Denormalized into API responses (see schemas/
        message.py) so any session can see this without a separate
        /users/ or /customers/ lookup.
        """
        if self.user:
            return self.user.full_name
        if self.customer:
            return f"{self.customer.first_name} {self.customer.last_name}"
        return None
