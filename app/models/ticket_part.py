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
        status: Fulfillment status -- "needed", "ordered", "shipped",
            "delayed", "delivered", "backordered", "received", or
            "installed". Free-text rather than a DB-level enum, since new
            statuses may need to be added without a migration; validate
            allowed values at the service/schema layer if that's ever
            needed.
        carrier: Who's physically delivering it -- e.g. "USPS", "UPS",
            "FedEx", "Amazon Logistics". Entered by hand from the retailer's
            shipping confirmation email; there's no reliable automated way
            to tie a shipping email back to a specific ticket (the email
            has no ticket reference, and not every part order is even for
            a specific customer -- some are shop stock replenishment).
        tracking_number: The carrier's tracking number, also entered by
            hand. Together with `carrier`, this is enough for a tech to
            look up the current shipment status themselves when a
            customer asks, without this app needing to poll any carrier
            API.
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

    carrier = Column(String, nullable=True)
    tracking_number = Column(String, nullable=True)

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
