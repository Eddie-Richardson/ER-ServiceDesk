# ER-ServiceDesk/alembic/versions/d8e2f4a6c9b1_add_quote_sent_at.py
"""add quote_sent_at to quotes

Revision ID: d8e2f4a6c9b1
Revises: a3c7e9f1b5d2
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "d8e2f4a6c9b1"
down_revision = "a3c7e9f1b5d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quotes", sa.Column("quote_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("quotes", "quote_sent_at")
