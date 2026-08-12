# ER-ServiceDesk/alembic/versions/e8b1d5f3a7c2_add_device_user_accounts.py
"""add device_user_accounts

Revision ID: e8b1d5f3a7c2
Revises: d4f7c2a9e1b3
Create Date: 2026-08-12

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "e8b1d5f3a7c2"
down_revision = "d4f7c2a9e1b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "device_user_accounts",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("account_name", sa.String(), nullable=False),
        sa.Column("encrypted_password", sa.String(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("device_user_accounts")
