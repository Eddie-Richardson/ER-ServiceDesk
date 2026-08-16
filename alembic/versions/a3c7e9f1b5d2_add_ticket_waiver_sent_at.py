# ER-ServiceDesk/alembic/versions/a3c7e9f1b5d2_add_ticket_waiver_sent_at.py
"""add waiver_sent_at to tickets

Revision ID: a3c7e9f1b5d2
Revises: f1a9c3e7b2d5
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a3c7e9f1b5d2"
down_revision = "f1a9c3e7b2d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("waiver_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tickets", "waiver_sent_at")
