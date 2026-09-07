# ER-ServiceDesk/alembic/versions/fb70bdfdfb44_drop_unused_created_updated_at.py
"""drop unused created_at/updated_at columns

Revision ID: fb70bdfdfb44
Revises: a3782c51a402
Create Date: 2026-09-07

Confirmed unused throughout the Sep 2026 audit -- never displayed,
never read by any backend logic. AuditLog now provides real
create/update tracking for every one of these models (Asset, Part,
and TicketPart's coverage was added specifically to make this
removal safe), making these columns pure dead weight.

Two fields are kept where they're genuinely used elsewhere:
- created_at stays on AuditLog (the audit system's own timestamp),
  BackgroundJob (displayed in background_jobs_tab.py), Customer and
  Ticket (both drive the customer auto-archive "last activity"
  logic), and Payment (displayed in invoice_detail_dialog.py).
- Note.updated_at is untouched entirely -- unlike every other field
  here, it's genuinely, correctly maintained for a real purpose
  (tracking edits), just not yet surfaced in the UI. Removing it
  would lose real, intended functionality, not just dead weight.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "fb70bdfdfb44"
down_revision = "a3782c51a402"
branch_labels = None
depends_on = None


# (table_name, column_name) pairs to drop
_DROP_BOTH = [
    "assets", "devices", "discounts", "invoices", "quotes", "parts",
    "services", "tax_rates", "ticket_parts", "users", "payment_plans",
]
_DROP_UPDATED_ONLY = [
    "audit_logs", "background_jobs", "customers", "payments", "tickets",
]


def upgrade() -> None:
    for table in _DROP_BOTH:
        op.drop_column(table, "created_at")
        op.drop_column(table, "updated_at")
    for table in _DROP_UPDATED_ONLY:
        op.drop_column(table, "updated_at")


def downgrade() -> None:
    import sqlalchemy as sa

    for table in _DROP_BOTH:
        op.add_column(table, sa.Column("created_at", sa.DateTime(timezone=True), nullable=True))
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
    for table in _DROP_UPDATED_ONLY:
        op.add_column(table, sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
