"""merge note into message -- one unified note/conversation system

Revision ID: ec97585605a1
Revises: c3d36e8efa62
Create Date: 2026-08-09 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec97585605a1'
down_revision: Union[str, Sequence[str], None] = 'c3d36e8efa62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # notes and messages were two separate, overlapping systems doing
    # the same underlying job -- a note that could optionally also
    # email the customer, and a customer reply that could only ever
    # become a message, never a note, with no way to see both
    # together. Merging into one: messages now covers every case
    # (internal-only, staff-authored-and-sent, and the customer's own
    # reply), and notes is dropped entirely rather than kept as dead
    # weight alongside it.
    op.drop_table('notes')

    # customer_id was required before -- now nullable, since an
    # internal-only entry (never emailed) has no customer involved at
    # all.
    op.alter_column('messages', 'customer_id', nullable=True)

    # user_id is new -- the staff author for internal/outbound
    # entries. Nullable, since an inbound entry (the customer's own
    # reply) has no staff author; it's attributed to customer_id
    # instead.
    op.add_column('messages', sa.Column('user_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'messages', 'users', ['user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(None, 'messages', type_='foreignkey')
    op.drop_column('messages', 'user_id')
    op.alter_column('messages', 'customer_id', nullable=False)

    op.create_table(
        'notes',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('ticket_id', sa.Integer(), sa.ForeignKey('tickets.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('sent_to_customer', sa.Boolean(), nullable=True),
        sa.Column('message_id', sa.Integer(), sa.ForeignKey('messages.id'), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
