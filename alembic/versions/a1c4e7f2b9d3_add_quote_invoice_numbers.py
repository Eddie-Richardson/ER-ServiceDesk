# ER-ServiceDesk/alembic/versions/a1c4e7f2b9d3_add_quote_invoice_numbers.py
"""add quote_number and invoice_number, decoupled from id

Revision ID: a1c4e7f2b9d3
Revises: e5f7a9c2b4d6
Create Date: 2026-08-23

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "a1c4e7f2b9d3"
down_revision = "e5f7a9c2b4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Added nullable first, then backfilled, then made NOT NULL --
    # can't add a NOT NULL column directly to a table that may already
    # have rows.
    op.add_column("quotes", sa.Column("quote_number", sa.Integer(), nullable=True))
    op.add_column("invoices", sa.Column("invoice_number", sa.Integer(), nullable=True))

    # Backfill from each row's own id, not a fresh 1, 2, 3... sequence.
    # A real shop may already have quotes/invoices with real numbers a
    # customer has actually seen on a printed or emailed document --
    # renumbering everything from scratch would silently disagree with
    # what's already out in the world. Using id preserves exactly what
    # was effectively already being shown as "Quote #X"/"Invoice #X"
    # up to this point, and only genuinely new numbering behavior
    # (business-facing numbers no longer tied to the database key)
    # takes effect on top of that for everything created going forward.
    op.execute("UPDATE quotes SET quote_number = id WHERE quote_number IS NULL")
    op.execute("UPDATE invoices SET invoice_number = id WHERE invoice_number IS NULL")

    op.alter_column("quotes", "quote_number", nullable=False)
    op.alter_column("invoices", "invoice_number", nullable=False)

    op.create_unique_constraint("quotes_quote_number_key", "quotes", ["quote_number"])
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"])
    op.create_unique_constraint("invoices_invoice_number_key", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])


def downgrade() -> None:
    op.drop_index("ix_invoices_invoice_number", table_name="invoices")
    op.drop_constraint("invoices_invoice_number_key", "invoices", type_="unique")
    op.drop_column("invoices", "invoice_number")

    op.drop_index("ix_quotes_quote_number", table_name="quotes")
    op.drop_constraint("quotes_quote_number_key", "quotes", type_="unique")
    op.drop_column("quotes", "quote_number")
