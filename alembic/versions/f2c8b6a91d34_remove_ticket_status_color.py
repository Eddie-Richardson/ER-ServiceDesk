"""remove unused color column from ticket_statuses

Revision ID: f2c8b6a91d34
Revises: e91a4c7d3f56
Create Date: 2026-07-24 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c8b6a91d34'
down_revision: Union[str, Sequence[str], None] = 'e91a4c7d3f56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema.

    Drops ticket_statuses.color. It was carried around in the schema
    and seed data from early on, but never actually rendered anywhere
    in the desktop UI -- Priority already provides the "how urgent"
    visual signal, so a second, unused color dimension on Status was
    redundant rather than a real feature waiting to be finished.
    """
    op.drop_column('ticket_statuses', 'color')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('ticket_statuses', sa.Column('color', sa.String(), nullable=True))
