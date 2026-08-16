# ER-ServiceDesk/alembic/versions/e5f7a9c2b4d6_add_invoice_sent_at.py
"""add invoice_sent_at to invoices

Revision ID: e5f7a9c2b4d6
Revises: d8e2f4a6c9b1
Create Date: 2026-08-16

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e5f7a9c2b4d6"
down_revision = "d8e2f4a6c9b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("invoice_sent_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("invoices", "invoice_sent_at")
