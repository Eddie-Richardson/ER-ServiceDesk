# ER-ServiceDesk/desktop/ticket_part_dialog.py

"""
Dialog for adding a new part requirement to a ticket, or editing an
existing one -- which part, how many, and where its fulfillment
status stands. Changing status here is what actually triggers the
customer notification worker (see app/services/ticket_part_service.py
server-side); the notification is genuinely wired to this action, not
just decorative.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError

# Matches app/workers/tasks.py's own _PART_STATUS_MESSAGES exactly,
# plus "needed" (the default status when a requirement is first
# recorded, before anything customer-notable has happened yet).
STATUS_OPTIONS = ["needed", "ordered", "shipped", "delayed", "backordered", "received", "installed"]


class TicketPartDialog(QDialog):
    """
    Modal dialog for creating or editing a part requirement on a ticket.

    Pass `ticket_part=None` to add a new one, or an existing record to
    edit it. On a successful save, the dialog closes itself and the
    saved record is available via `self.saved_ticket_part`.
    """

    def __init__(self, ticket_id: int, parts: list[dict], ticket_part: dict | None = None, parent=None):
        """
        Args:
            ticket_id: The ticket this part requirement belongs to.
            parts: Every part in inventory, for the picker.
        """
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.parts = parts
        self.ticket_part = ticket_part
        self.saved_ticket_part: dict | None = None
        self.deleted = False

        self.setWindowTitle("Edit Part" if ticket_part else "Add Part")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()
        if ticket_part:
            self._prefill_from_ticket_part(ticket_part)

    def _build_ui(self):
        """Builds the Part picker, Quantity, Status, Carrier, Tracking, and Notes fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.part_combo = QComboBox()
        # Editing an existing requirement's part-vs-quantity is
        # unusual in practice (the requirement is what changed, not
        # which part it is) -- keep this simple by disabling the part
        # picker on edit, matching how a ticket's own customer picker
        # similarly doesn't get casually reassigned after creation.
        for part in self.parts:
            self.part_combo.addItem(part.get("name", ""), userData=part["id"])
        if self.ticket_part:
            self.part_combo.setEnabled(False)

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999)
        self.quantity_input.setValue(1)

        self.status_combo = QComboBox()
        for status in STATUS_OPTIONS:
            self.status_combo.addItem(status.capitalize(), userData=status)

        self.carrier_input = QLineEdit()
        self.carrier_input.setPlaceholderText("Carrier, e.g. UPS (optional)")
        self.carrier_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.tracking_input = QLineEdit()
        self.tracking_input.setPlaceholderText("Tracking number (optional)")
        self.tracking_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes, e.g. supplier order number (optional)")
        self.notes_input.setFixedHeight(60)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        self.delete_button = None
        if self.ticket_part:
            self.delete_button = QPushButton("Remove Part")
            self.delete_button.setObjectName("danger")
            self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
            self.delete_button.clicked.connect(self._attempt_delete)

        for label_text, widget in [
            ("Part", self.part_combo),
            ("Quantity Needed", self.quantity_input),
            ("Status", self.status_combo),
            ("Carrier", self.carrier_input),
            ("Tracking Number", self.tracking_input),
            ("Notes", self.notes_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        if self.delete_button:
            outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)

    def _prefill_from_ticket_part(self, ticket_part: dict):
        index = self.part_combo.findData(ticket_part.get("part_id"))
        if index >= 0:
            self.part_combo.setCurrentIndex(index)

        self.quantity_input.setValue(ticket_part.get("quantity_needed", 1))

        status_index = self.status_combo.findData(ticket_part.get("status", "needed"))
        if status_index >= 0:
            self.status_combo.setCurrentIndex(status_index)

        self.carrier_input.setText(ticket_part.get("carrier") or "")
        self.tracking_input.setText(ticket_part.get("tracking_number") or "")
        self.notes_input.setPlainText(ticket_part.get("notes") or "")

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then saves synchronously -- a small, infrequent action, not worth the complexity of a background thread."""
        part_id = self.part_combo.currentData()
        if part_id is None:
            self._show_error("Select a part.")
            return

        payload = {
            "quantity_needed": self.quantity_input.value(),
            "status": self.status_combo.currentData(),
            "carrier": self.carrier_input.text().strip() or None,
            "tracking_number": self.tracking_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
        }

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        try:
            if self.ticket_part:
                result = api_client.update_ticket_part(self.ticket_part["id"], payload)
            else:
                payload["ticket_id"] = self.ticket_id
                payload["part_id"] = part_id
                result = api_client.create_ticket_part(payload)
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Save")
            self._show_error(str(e))
            return

        self.save_button.setEnabled(True)
        self.save_button.setText("Save")
        self.saved_ticket_part = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete(self):
        """Confirms, then removes this part requirement from the ticket."""
        confirmed = QMessageBox.question(
            self,
            "Remove Part",
            "Remove this part from the ticket? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)
        try:
            api_client.delete_ticket_part(self.ticket_part["id"])
        except ApiError as e:
            self._show_error(str(e))
            return
        finally:
            self.delete_button.setEnabled(True)

        self.deleted = True
        self.accept()
