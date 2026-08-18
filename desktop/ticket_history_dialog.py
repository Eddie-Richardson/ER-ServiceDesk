# ER-ServiceDesk/desktop/ticket_history_dialog.py

"""
Shows a ticket's full history -- status changes AND general activity
(created, updated, an inbound email matching, an outbound notification
sending or failing) -- merged into one chronological timeline, oldest
first.

StatusHistory and AuditLog stay two separate tables underneath
(StatusHistory keeps its own structured, reportable shape; AuditLog
stays the general cross-entity trail) -- this dialog is where they get
merged visually, so there's one place to look rather than two.

Deliberately read-only -- no composer, no edit/delete of any kind,
matching both backends' own design: this is meant to be an immutable
record, not something a tech can rewrite after the fact.

Fully synchronous, no QThread -- same reasoning as notes_dialog.py:
this is a small, infrequent action, and the simplest safe choice is
not introducing a background thread at all.

Only ever opened for an EXISTING ticket -- ticket_form_dialog.py only
shows the "History" button once a ticket has actually been saved once.
"""

from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client
from desktop.api_client import ApiError
from desktop.window_geometry import restore_geometry, save_geometry

# Human-readable header for each AuditLog action this dialog might
# show. Falls back to the raw action string (title-cased) for anything
# not listed here, so a new action added elsewhere doesn't need this
# dialog updated in lockstep to still show something reasonable.
_ACTION_LABELS = {
    "ticket_created": "Ticket Created",
    "ticket_updated": "Ticket Updated",
    "inbound_email_matched": "Customer Reply Received",
    "outbound_notification_sent": "Email Sent to Customer",
    "outbound_notification_failed": "Email Failed to Send",
}


def _format_timestamp(iso_string: str) -> str:
    """Formats an ISO datetime string for display, e.g. 'Aug 8, 2026 3:45 PM'. Returns the raw string unchanged if it can't be parsed."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %-d, %Y %-I:%M %p")
    except (ValueError, TypeError):
        return iso_string or ""


def _status_history_to_timeline_entry(entry: dict) -> dict:
    """Normalizes a StatusHistory record into this dialog's common timeline shape."""
    status_name = entry.get("status_name") or "Unknown"
    changed_by_name = entry.get("changed_by_name") or "Unknown"
    return {
        "timestamp": entry.get("changed_at", ""),
        "header": f"Changed to: {status_name}",
        "detail_line": f"By {changed_by_name}",
    }


def _audit_log_to_timeline_entry(entry: dict) -> dict:
    """Normalizes an AuditLog record into this dialog's common timeline shape."""
    action = entry.get("action", "")
    header = _ACTION_LABELS.get(action, action.replace("_", " ").title())
    user_name = entry.get("user_name") or "System"
    details = entry.get("details")
    detail_line = f"By {user_name}" + (f" -- {details}" if details else "")
    return {
        "timestamp": entry.get("created_at", ""),
        "header": header,
        "detail_line": detail_line,
    }


class TicketHistoryDialog(QDialog):
    """Read-only, chronological view of a ticket's status changes and general activity, merged into one timeline."""

    def __init__(self, ticket_id: int, ticket_title: str, parent=None):
        """
        Args:
            ticket_title: Shown in the window title for context.
        """
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.setWindowTitle(f"History - {ticket_title}")
        self.resize(500, 400)
        self._build_ui()
        restore_geometry(self, "ticket_history_dialog")
        self._load_history()

    def _build_ui(self):
        """Builds the scrollable, empty-to-start entry list."""
        layout = QVBoxLayout()

        self.entries_container = QWidget()
        self.entries_layout = QVBoxLayout()
        self.entries_layout.addStretch()
        self.entries_container.setLayout(self.entries_layout)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(self.entries_container)
        layout.addWidget(scroll_area)

        self.setLayout(layout)

    def closeEvent(self, event):
        """Saves this dialog's size/position before closing, matching every other window in this app."""
        save_geometry(self, "ticket_history_dialog")
        super().closeEvent(event)

    def _load_history(self):
        """Fetches both StatusHistory and AuditLog for this ticket, merges, and renders them as one timeline."""
        try:
            status_entries = api_client.list_status_history_for_ticket(self.ticket_id)
        except ApiError as e:
            self._show_error(f"Could not load status history: {e}")
            return

        try:
            audit_entries = api_client.list_audit_log_for_ticket(self.ticket_id)
        except ApiError as e:
            self._show_error(f"Could not load activity history: {e}")
            return

        timeline = (
            [_status_history_to_timeline_entry(e) for e in status_entries]
            + [_audit_log_to_timeline_entry(e) for e in audit_entries]
        )
        timeline.sort(key=lambda e: e["timestamp"])

        if not timeline:
            empty_label = QLabel("No history recorded yet.")
            self.entries_layout.insertWidget(0, empty_label)
            return

        for entry in timeline:
            card = self._build_entry_card(entry)
            self.entries_layout.insertWidget(self.entries_layout.count() - 1, card)

    def _show_error(self, message: str):
        error_label = QLabel(message)
        error_label.setWordWrap(True)
        self.entries_layout.insertWidget(0, error_label)

    def _build_entry_card(self, entry: dict) -> QWidget:
        """Builds a single timeline entry's display widget."""
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card_layout = QVBoxLayout()

        header_label = QLabel(entry["header"])
        header_label.setStyleSheet("font-weight: bold;")
        card_layout.addWidget(header_label)

        when = _format_timestamp(entry["timestamp"])
        detail_label = QLabel(f"{entry['detail_line']} - {when}")
        detail_label.setWordWrap(True)
        card_layout.addWidget(detail_label)

        card.setLayout(card_layout)
        return card
