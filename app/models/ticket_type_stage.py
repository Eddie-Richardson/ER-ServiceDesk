# ER-ServiceDesk/app/models/ticket_type_stage.py
# Join model restricting which stages are valid for which ticket type
"""
Many-to-many allow-list: declares which TicketStage values are valid for
a given TicketType (e.g. "Burn-in Test" only makes sense for a custom
build type, not a simple repair type). Ticket creation/update is validated
against this table in TicketService -- but only once at least one entry
exists for a given type, so restrictions are opt-in per type rather than
locking out stages the shop hasn't configured yet.
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from app.db.base import Base


class TicketTypeStage(Base):
    """
    Represents one allowed (ticket type, stage) pairing.

    Attributes:
        id: Primary key.
        type_id: The ticket type this stage is valid for.
        stage_id: The stage allowed for that ticket type.
    """
    __tablename__ = "ticket_type_stages"
    __table_args__ = (UniqueConstraint("type_id", "stage_id", name="uq_ticket_type_stage"),)

    id = Column(Integer, primary_key=True, index=True)
    type_id = Column(Integer, ForeignKey("ticket_types.id"), nullable=False)
    stage_id = Column(Integer, ForeignKey("ticket_stages.id"), nullable=False)

    ticket_type = relationship("TicketType", back_populates="allowed_stages")
    stage = relationship("TicketStage", back_populates="allowed_for_types")
