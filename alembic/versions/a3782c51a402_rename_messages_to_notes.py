# ER-ServiceDesk/alembic/versions/a3782c51a402_rename_messages_to_notes.py
"""rename messages/message_templates tables to notes/note_templates

Revision ID: a3782c51a402
Revises: 2657c569aee8
Create Date: 2026-09-07

The desktop UI has always called this feature "Notes"; the backend
never matched, still using "Message" throughout (model, schema,
routes, CRUD, service) -- confirmed during the Sep 2026 audit. This
renames the underlying tables to match the rest of the rename
(model/schema/route/CRUD/service files, class names, and the API
endpoint paths were all renamed alongside this).
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a3782c51a402"
down_revision = "2657c569aee8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.rename_table("messages", "notes")
    op.rename_table("message_templates", "note_templates")


def downgrade() -> None:
    op.rename_table("notes", "messages")
    op.rename_table("note_templates", "message_templates")
