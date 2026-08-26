# ER-ServiceDesk/alembic/versions/d4e8f1a6c9b3_add_location_show_in_ticket_picker.py
"""add locations.show_in_ticket_picker

Revision ID: d4e8f1a6c9b3
Revises: c8f2a5d9e3b7
Create Date: 2026-08-25

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4e8f1a6c9b3"
down_revision = "c8f2a5d9e3b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("locations", sa.Column("show_in_ticket_picker", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("locations", "show_in_ticket_picker")
