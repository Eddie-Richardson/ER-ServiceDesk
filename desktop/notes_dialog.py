# ER-ServiceDesk/desktop/notes_dialog.py

"""
Shows a ticket's full note/conversation history in one place -- staff
internal notes, messages actually sent to the customer, and the
customer's own replies, together in one chronological timeline. Lets
a tech add a new entry, either internal-only or emailed to the
customer.

Backed by the merged Message system (see app/models/message.py) --
internal notes and customer email exchange live in one unified
backend system, so this dialog shows everything on the ticket, one
real history instead of split across separate views.

Deliberately fully synchronous -- every action (list/create/update/
delete) runs directly on the main thread, no QThread and no
cross-thread signal delivery anywhere in this file. This removes an
entire category of background-thread risk. The tradeoff is a brief UI
pause during each action (a network round-trip on small text payloads
-- near-instant on a local network), a clearly worthwhile trade
against that risk.

Modal (exec, not show) -- avoids real, platform-specific input-routing
behavior that comes from mixing a modal parent (the ticket form this
opens from) with a non-modal child; this matters on Windows
specifically.

Every entry is visible to anyone who can open this dialog at all (full
history, shared -- not private to whoever wrote it), but Edit/Delete
only appear if the current session is allowed to touch that SPECIFIC
entry -- its own author, a superuser, or (for a customer's own inbound
reply, which has no staff author at all) a superuser only. This is a
UI convenience mirroring the same rule enforced server-side (see
message_service.py); the backend enforces it independently regardless
of what buttons this dialog happens to show.

Only ever opened for an EXISTING ticket (needs a real ticket_id to
attach entries to) -- ticket_form_dialog.py only shows the "Notes"
button once a ticket has actually been saved once.
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, session
from desktop.api_client import ApiError
from desktop.window_geometry import restore_geometry, save_geometry


def _format_timestamp(iso_string: str) -> str:
    """Formats an ISO datetime string for display, e.g. 'Aug 8, 2026 3:45 PM'. Returns the raw string unchanged if it can't be parsed."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %-d, %Y %-I:%M %p")
    except (ValueError, TypeError):
        return iso_string or ""


class NotesDialog(QDialog):
    """Full note/conversation timeline + composer for a single ticket."""

    def __init__(self, ticket_id: int, ticket_title: str, customer_id: int | None, parent=None):
        """
        Args:
            ticket_title: Shown in the window title for context.
            customer_id: This ticket's customer, needed when an entry
                is sent to the customer. Passed directly by the caller
                (which already has the full ticket dict) rather than
                re-fetched here.
        """
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.ticket_title = ticket_title
        self.customer_id = customer_id
        self.setWindowTitle(f"Notes - {ticket_title}")
        self.resize(600, 500)
        self._build_ui()
        restore_geometry(self, "notes_dialog")
        self._refresh_entries()

    def _build_ui(self):
        """Builds the scrollable timeline and the composer at the bottom."""
        layout = QVBoxLayout()

        self.entries_container = QWidget()
        self.entries_layout = QVBoxLayout()
        self.entries_layout.addStretch()
        self.entries_container.setLayout(self.entries_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.entries_container)
        layout.addWidget(scroll_area, stretch=1)

        composer_frame = QFrame()
        composer_frame.setFrameShape(QFrame.Shape.StyledPanel)
        composer_layout = QVBoxLayout()

        self.template_combo = QComboBox()
        self.template_combo.addItem("Insert Template...", userData=None)
        self.template_combo.currentIndexChanged.connect(self._on_template_selected)
        composer_layout.addWidget(self.template_combo)
        self._load_templates()

        self.composer_input = QTextEdit()
        self.composer_input.setPlaceholderText("Add a note...")
        self.composer_input.setFixedHeight(80)
        composer_layout.addWidget(self.composer_input)

        self.send_to_customer_checkbox = QCheckBox("Also email this note to the customer")
        composer_layout.addWidget(self.send_to_customer_checkbox)

        self.add_note_button = QPushButton("Add Note")
        self.add_note_button.clicked.connect(self._on_add_note)
        composer_layout.addWidget(self.add_note_button)

        composer_frame.setLayout(composer_layout)
        layout.addWidget(composer_frame)

        self.setLayout(layout)

    def closeEvent(self, event):
        """Saves this dialog's size/position before closing, matching every other window in this app."""
        save_geometry(self, "notes_dialog")
        super().closeEvent(event)

    # -- Message templates (composer quick-insert) --

    def _load_templates(self):
        """Fills the template dropdown with every available template. Silently leaves just the placeholder if this fails -- not critical to the dialog's main purpose."""
        try:
            templates = api_client.list_message_templates()
        except ApiError:
            return
        for template in templates:
            self.template_combo.addItem(template["name"], userData=template)

    def _on_template_selected(self, index: int):
        """
        Inserts the selected template's body into the composer, with
        {ticket_id} and {ticket_title} substituted in. Asks for
        confirmation first if the composer already has text, so a
        tech can't lose something they'd already typed by accident.
        Resets the dropdown back to the placeholder afterward, so the
        same (or another) template can be inserted again later.
        """
        template = self.template_combo.itemData(index)
        if template is None:
            return

        if self.composer_input.toPlainText().strip():
            confirmed = QMessageBox.question(
                self,
                "Replace Current Text?",
                "This will replace what you've already typed. Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                self.template_combo.setCurrentIndex(0)
                return

        body = template.get("body", "")
        body = body.replace("{ticket_id}", str(self.ticket_id)).replace("{ticket_title}", self.ticket_title)
        self.composer_input.setPlainText(body)
        self.template_combo.setCurrentIndex(0)

    # -- Loading and rendering --

    def _refresh_entries(self):
        """Reloads the full timeline for this ticket from the backend."""
        try:
            entries = api_client.list_messages_for_ticket(self.ticket_id)
        except ApiError as e:
            QMessageBox.critical(self, "Action Failed", str(e))
            return
        self._render_entries(entries)

    def _render_entries(self, entries: list[dict]):
        """Clears and rebuilds the timeline display from fresh data, oldest first."""
        while self.entries_layout.count() > 1:
            item = self.entries_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        entries_sorted = sorted(entries, key=lambda e: e.get("created_at", ""))
        for entry in entries_sorted:
            card = self._build_entry_card(entry)
            self.entries_layout.insertWidget(self.entries_layout.count() - 1, card)

    def _build_entry_card(self, entry: dict) -> QWidget:
        """
        Builds a single timeline entry's display widget, visually
        distinguished by direction, including Edit/Delete if the
        current session is allowed to touch this specific entry.
        """
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout()

        direction = entry.get("direction")
        badge = {
            "internal": "[Internal]",
            "outbound": "[Sent to customer]",
            "inbound": "[Customer reply]",
        }.get(direction, "")

        header_text = f"{badge} {entry.get('author_name') or 'Unknown'} - {_format_timestamp(entry.get('created_at', ''))}"
        if direction == "outbound":
            status = entry.get("email_status") or "pending"
            header_text += f"  (email: {status})"
        header_label = QLabel(header_text)
        header_label.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(header_label)

        content_label = QLabel(entry.get("content", ""))
        content_label.setWordWrap(True)
        card_layout.addWidget(content_label)

        # Author-or-superuser for staff-authored entries (internal/
        # outbound); superuser-only for inbound, which has no staff
        # author to defer to. Mirrors message_service.py's own rule --
        # this is a UI convenience, not the real enforcement.
        user_id = entry.get("user_id")
        can_edit = (
            (user_id is not None and (user_id == session.current_user_id() or session.is_superuser()))
            or (user_id is None and session.is_superuser())
        )
        if can_edit:
            button_row = QHBoxLayout()
            edit_button = QPushButton("Edit")
            edit_button.clicked.connect(lambda: self._on_edit_entry(entry))
            button_row.addWidget(edit_button)

            delete_button = QPushButton("Delete")
            delete_button.clicked.connect(lambda: self._on_delete_entry(entry))
            button_row.addWidget(delete_button)

            button_row.addStretch()
            card_layout.addLayout(button_row)

        card.setLayout(card_layout)
        return card

    # -- Actions --

    def _on_add_note(self):
        """Validates and submits a new entry -- internal, or outbound if the checkbox is toggled on."""
        content = self.composer_input.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "Empty Note", "Please enter some text for the note.")
            return

        send_to_customer = self.send_to_customer_checkbox.isChecked()
        payload = {
            "ticket_id": self.ticket_id,
            "user_id": session.current_user_id(),
            "direction": "outbound" if send_to_customer else "internal",
            "content": content,
        }
        if send_to_customer:
            if self.customer_id is None:
                QMessageBox.critical(self, "Action Failed", "This ticket has no customer on file -- the note was not sent.")
                return
            payload["customer_id"] = self.customer_id

        self.add_note_button.setEnabled(False)
        try:
            api_client.create_message(payload)
        except ApiError as e:
            QMessageBox.critical(self, "Action Failed", str(e))
            return
        finally:
            self.add_note_button.setEnabled(True)

        self.composer_input.clear()
        self.send_to_customer_checkbox.setChecked(False)
        self._refresh_entries()

    def _on_edit_entry(self, entry: dict):
        """Opens a small edit dialog for this entry's content, then saves if confirmed."""
        dialog = _EditNoteDialog(entry.get("content", ""), self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_content = dialog.new_content()
            if new_content:
                try:
                    api_client.update_message(entry["id"], {"content": new_content})
                except ApiError as e:
                    QMessageBox.critical(self, "Action Failed", str(e))
                    return
                self._refresh_entries()

    def _on_delete_entry(self, entry: dict):
        """Confirms, then deletes an entry."""
        confirm = QMessageBox.question(
            self,
            "Delete Note",
            "Delete this entry? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            api_client.delete_message(entry["id"])
        except ApiError as e:
            QMessageBox.critical(self, "Action Failed", str(e))
            return
        self._refresh_entries()


class _EditNoteDialog(QDialog):
    """Minimal dialog for editing a single entry's content."""

    def __init__(self, current_content: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Note")
        self.resize(400, 200)

        layout = QVBoxLayout()
        self.content_input = QTextEdit()
        self.content_input.setPlainText(current_content)
        layout.addWidget(self.content_input)

        button_row = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.accept)
        button_row.addWidget(save_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_row.addWidget(cancel_button)
        layout.addLayout(button_row)

        self.setLayout(layout)

    def new_content(self) -> str:
        """Returns the edited text, stripped -- empty if the admin cleared it entirely."""
        return self.content_input.toPlainText().strip()
