# ER-ServiceDesk/alembic/versions/c256a0833c10_drop_invoice_quote_details.py
"""drop invoices.details and quotes.details

Revision ID: c256a0833c10
Revises: e7b3c6f9a2d5
Create Date: 2026-09-06

Removes a field that was never actually set or displayed anywhere on
either model, on the desktop side or the backend -- confirmed during
the Sep 2026 audit.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "c256a0833c10"
down_revision = "e7b3c6f9a2d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("invoices", "details")
    op.drop_column("quotes", "details")


def downgrade() -> None:
    op.add_column("invoices", sa.Column("details", sa.Text(), nullable=True))
    op.add_column("quotes", sa.Column("details", sa.Text(), nullable=True))
