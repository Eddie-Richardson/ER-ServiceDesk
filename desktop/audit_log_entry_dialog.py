# ER-ServiceDesk/desktop/audit_log_entry_dialog.py

"""
Read-only popup showing a single audit log entry's full details.

The table row itself is too cramped to read a genuinely long details
message (multiple changed fields, each with real before/after values) --
this shows the same entry with room to actually read it, splitting
multiple changed fields onto their own lines rather than one long,
semicolon-separated line.
"""

from PySide6.QtWidgets import (
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.base_dialog import AppDialog
from desktop.formatting import format_timestamp
from desktop.window_geometry import restore_geometry, save_geometry


class AuditLogEntryDialog(AppDialog):
    """Modal, read-only dialog showing one audit log entry's full details."""

    def __init__(self, entry: dict, parent=None):
        """
        Args:
            entry: The audit log entry dict, as returned by
                api_client.list_audit_logs() -- already formatted for
                display by the caller (timestamp, entity label, etc.).
        """
        super().__init__(parent)
        self.entry = entry

        self.setWindowTitle("Audit Log Entry")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "AuditLogEntryDialog")

        self._build_ui()

    def closeEvent(self, event):
        save_geometry(self, "AuditLogEntryDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the summary labels and the details text area."""
        content = QWidget()
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        for label_text, value in [
            ("Timestamp", format_timestamp(self.entry.get("created_at", ""))),
            ("User", self.entry.get("user_name") or "System"),
            ("Action", self.entry.get("action", "")),
            ("Entity", f"{self.entry.get('entity_type', '')} #{self.entry.get('entity_id', '')}"),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            outer_layout.addWidget(value_label)

        details_label = QLabel("Details")
        details_label.setObjectName("subtitle")
        outer_layout.addWidget(details_label)

        details_text = QTextEdit()
        details_text.setReadOnly(True)
        # Multiple changed fields arrive as one "; "-separated string
        # (see ticket_service.update()) -- splitting them onto their
        # own lines here is purely a display choice, not a change to
        # what's actually stored.
        raw_details = self.entry.get("details") or ""
        details_text.setPlainText("\n".join(part.strip() for part in raw_details.split(";") if part.strip()))
        details_text.setMinimumHeight(120)
        outer_layout.addWidget(details_text)

        close_button = QPushButton("Close")
        close_button.setFixedHeight(layout.BUTTON_HEIGHT)
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        content.setLayout(outer_layout)
        self.set_scrollable_content(content)
