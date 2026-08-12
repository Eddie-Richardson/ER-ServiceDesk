# ER-ServiceDesk/alembic/versions/d4f7c2a9e1b3_add_dropoff_form_fields.py
"""add pickup_person/accessories_included to tickets, os/edition to devices

Revision ID: d4f7c2a9e1b3
Revises: c9e2a4f7b1d6
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d4f7c2a9e1b3"
down_revision = "c9e2a4f7b1d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tickets", sa.Column("pickup_person", sa.String(), nullable=True))
    op.add_column("tickets", sa.Column("accessories_included", sa.String(), nullable=True))
    op.add_column("devices", sa.Column("os", sa.String(), nullable=True))
    op.add_column("devices", sa.Column("edition", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("devices", "edition")
    op.drop_column("devices", "os")
    op.drop_column("tickets", "accessories_included")
    op.drop_column("tickets", "pickup_person")
