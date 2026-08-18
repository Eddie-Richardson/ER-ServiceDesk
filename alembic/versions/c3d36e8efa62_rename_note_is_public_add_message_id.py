"""rename note is_public to sent_to_customer, add message_id link

Revision ID: c3d36e8efa62
Revises: b8e3d15f9a27
Create Date: 2026-08-08 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d36e8efa62'
down_revision: Union[str, Sequence[str], None] = 'b8e3d15f9a27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # is_public -> sent_to_customer: renamed for clarity. The old name
    # read as a passive visibility flag ("would this be shown on a
    # customer-facing view"); what it actually needs to represent is
    # an event record -- was this specific note emailed to the
    # customer -- which sent_to_customer states plainly.
    op.alter_column('notes', 'is_public', new_column_name='sent_to_customer')

    # Links a sent note to the Message record it produced, so the note
    # history UI can show real delivery status (Message.email_status)
    # without duplicating that tracking. Nullable -- only set for
    # notes actually sent to the customer; an internal-only note has
    # nothing to link to.
    op.add_column('notes', sa.Column('message_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'notes', 'messages', ['message_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'notes', type_='foreignkey')
    op.drop_column('notes', 'message_id')
    op.alter_column('notes', 'sent_to_customer', new_column_name='is_public')
