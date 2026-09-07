# ER-ServiceDesk/alembic/versions/2657c569aee8_asset_serial_number_required.py
"""make assets.serial_number required

Revision ID: 2657c569aee8
Revises: c256a0833c10
Create Date: 2026-09-07

serial_number was the only field on Asset with a genuine unique
constraint, but being nullable meant it couldn't reliably identify
every asset -- any number of assets could all have no serial number
at once. No data migration needed: this app isn't live yet, every
install is fresh test data.
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "2657c569aee8"
down_revision = "c256a0833c10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("assets", "serial_number", nullable=False)


def downgrade() -> None:
    op.alter_column("assets", "serial_number", nullable=True)
