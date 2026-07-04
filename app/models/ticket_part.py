# ER-ServiceDesk/app/models/ticket_part.py
# ORM model linking a ticket to the parts it needs
"""
Join model tracking which parts a ticket needs, how many, and where that
need stands (needed / ordered / backordered / received / installed). This
is the record a background job watches to auto-notify the customer when
a part's status changes.
"""

import datetime
from sqlalchemy import Integer, Column, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base


class TicketPart(Base):
    """
    Represents a single part requirement on a ticket, and its fulfillment
    status.

    Attributes:
        id: Primary key.
        ticket_id: The ticket that needs this part.
        part_id: The part that is needed.
        quantity_needed: How many units of the part this ticket needs.
        status: Fulfillment status -- "needed", "ordered", "backordered",
            "received", or "installed".
        ordered_at: When the part was ordered, if applicable.
        received_at: When the part arrived, if applicable.
        notes: Optional free-text notes (e.g. supplier order number).
        created_at: Timestamp the record was created.
        updated_at: Timestamp the record was last updated.
    """
    __tablename__ = "ticket_parts"

    id = Column(Integer, primary_key=True, index=True)

    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False)
    part_id = Column(Integer, ForeignKey("parts.id"), nullable=False)

    quantity_needed = Column(Integer, nullable=False, default=1)
    status = Column(String, nullable=False, default="needed", index=True)

    ordered_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(String, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.UTC),
        onupdate=lambda: datetime.datetime.now(datetime.UTC),
        nullable=False,
    )

    ticket = relationship("Ticket", back_populates="parts_needed")
    part = relationship("Part", back_populates="ticket_parts")
