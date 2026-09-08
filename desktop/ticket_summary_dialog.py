# ER-ServiceDesk/desktop/ticket_summary_dialog.py

"""
Read-only dialog for viewing a single ticket's key details, opened from
a customer profile's ticket-history sub-table.

Deliberately not editable, and deliberately not the full
TicketFormDialog -- that dialog needs a much larger set of reference
data (categories, types, the full assignable-users list) that isn't
part of what the Customers window loads, and a customer's own history
view has no real need for in-place editing anyway. Includes a "View
Notes" button that opens the real, existing NotesDialog for this
ticket, since that dialog already works independently and only needs
a ticket_id.
"""

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from desktop import layout
from desktop.base_dialog import AppDialog
from desktop.notes_dialog import NotesDialog
from desktop.window_geometry import restore_geometry, save_geometry


class TicketSummaryDialog(AppDialog):
    """Modal, read-only dialog showing one ticket's key details."""

    def __init__(self, ticket: dict, status_name: str, device: dict | None, parent=None):
        """
        Args:
            ticket: The ticket dict to display.
            status_name: This ticket's status_id already resolved to a
                readable name by the caller -- this dialog has no
                access to the full statuses list itself.
            device: This ticket's device dict, if found in the
                caller's already-loaded device list, else None (shown
                as "-" rather than failing).
        """
        super().__init__(parent)
        self.ticket = ticket

        self.setWindowTitle(f"Ticket #{ticket['id']} - {ticket.get('title', '')}")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "TicketSummaryDialog")

        self._build_ui(status_name, device)

    def closeEvent(self, event):
        save_geometry(self, "TicketSummaryDialog")
        super().closeEvent(event)

    def _build_ui(self, status_name: str, device: dict | None):
        """Builds a simple, read-only field list plus the View Notes and Close buttons."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        device_text = "-"
        if device:
            device_text = f"{device.get('brand') or ''} {device.get('model') or ''}".strip() or device.get("device_type", "-")

        fields = [
            ("Title", self.ticket.get("title", "")),
            ("Status", status_name),
            ("Priority", self.ticket.get("priority", "-")),
            ("Device", device_text),
            ("Opened", (self.ticket.get("created_at") or "")[:10] or "-"),
            ("Description", self.ticket.get("description") or "-"),
        ]
        for label_text, value in fields:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)

            value_label = QLabel(str(value))
            value_label.setWordWrap(True)
            outer_layout.addWidget(value_label)

        outer_layout.addSpacing(layout.SPACE_SM)

        notes_button = QPushButton("View Notes")
        notes_button.clicked.connect(self._on_view_notes)
        outer_layout.addWidget(notes_button)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        self.setLayout(outer_layout)

    def _on_view_notes(self):
        """Opens the real, existing NotesDialog for this ticket."""
        dialog = NotesDialog(self.ticket["id"], self.ticket.get("title", "Ticket"), self.ticket.get("customer_id"), parent=self)
        dialog.exec()
