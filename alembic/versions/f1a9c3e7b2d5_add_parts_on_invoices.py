# ER-ServiceDesk/alembic/versions/f1a9c3e7b2d5_add_parts_on_invoices.py
"""add parts on invoices: selling_price, line item part_id/part_name

Revision ID: f1a9c3e7b2d5
Revises: e8b1d5f3a7c2
Create Date: 2026-08-15

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "f1a9c3e7b2d5"
down_revision = "e8b1d5f3a7c2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parts", sa.Column("selling_price", sa.Numeric(), nullable=True))

    # service_name was NOT NULL on both quote_line_items AND
    # invoice_line_items -- relaxing both here, since a part line item
    # now has no service_name at all.
    op.alter_column("quote_line_items", "service_name", nullable=True)
    op.alter_column("invoice_line_items", "service_name", nullable=True)

    op.add_column("quote_line_items", sa.Column("part_id", sa.Integer(), sa.ForeignKey("parts.id", ondelete="SET NULL"), nullable=True))
    op.add_column("quote_line_items", sa.Column("part_name", sa.String(), nullable=True))

    op.add_column("invoice_line_items", sa.Column("part_id", sa.Integer(), sa.ForeignKey("parts.id", ondelete="SET NULL"), nullable=True))
    op.add_column("invoice_line_items", sa.Column("part_name", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("invoice_line_items", "part_name")
    op.drop_column("invoice_line_items", "part_id")
    op.drop_column("quote_line_items", "part_name")
    op.drop_column("quote_line_items", "part_id")
    op.alter_column("invoice_line_items", "service_name", nullable=False)
    op.alter_column("quote_line_items", "service_name", nullable=False)
    op.drop_column("parts", "selling_price")
