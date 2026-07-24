"""add must_change_password to users

Revision ID: e91a4c7d3f56
Revises: d7e2b9c4f108
Create Date: 2026-07-24 01:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e91a4c7d3f56'
down_revision: Union[str, Sequence[str], None] = 'd7e2b9c4f108'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Adds must_change_password to users, defaulting existing rows to
    False -- accounts that already exist (seeded admin/agent/front desk
    test accounts, or any real account created before this feature
    existed) keep working with their current password rather than
    being suddenly forced to change it. The flag only gets set True
    going forward, when an admin creates a new account or resets one.
    """
    op.add_column(
        'users',
        sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'must_change_password')
