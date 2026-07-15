# ER-ServiceDesk/desktop/ticket_form_dialog.py

"""
Dialog for creating a new ticket or editing an existing one.

Every foreign-keyed field (customer, device, category, type, status,
assigned technician) is a dropdown populated from the backend -- never
free text -- so a ticket can never reference a category or status that
doesn't actually exist. Customer uses a searchable/type-ahead combo box
since that list can grow large; everything else is a small fixed list,
so a plain dropdown is enough. Priority is a fixed four-level list
(Low/Medium/High/Urgent) rather than a backend lookup table -- see
project notes for why.

Assigned To always offers "Unassigned" and "Me" (self-assignment), using
the current user's own id from their JWT claims -- no API call needed,
and it works regardless of role. The backend's /users endpoint is
superuser-only, so the full technician list is only added to the dropdown
when the session has permission to fetch it; regular agents simply don't
see other technicians as assignment targets yet.
"""

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from desktop import layout, session
from desktop.ticket_save_worker import TicketSaveWorker

PRIORITY_LEVELS = ["Low", "Medium", "High", "Urgent"]
DEFAULT_STATUS_NAME = "Open"


class TicketFormDialog(QDialog):
    """
    Modal dialog for creating or editing a ticket.

    Pass `ticket=None` to create a new ticket, or an existing ticket dict
    (as returned by GET /tickets/) to edit one. On a successful save, the
    dialog closes itself and the saved ticket record is available via
    `self.saved_ticket`.
    """

    def __init__(self, reference_data: dict, ticket: dict | None = None, parent=None):
        """
        Args:
            reference_data: Dict with keys "statuses", "categories",
                "types", "customers", "devices", "users" -- the lookup
                lists loaded by TicketsDataWorker. "users" is empty for
                non-superuser sessions.
            ticket: An existing ticket dict to edit, or None to create
                a new one.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.reference_data = reference_data
        self.ticket = ticket
        self.saved_ticket: dict | None = None

        self._thread: QThread | None = None
        self._worker: TicketSaveWorker | None = None

        self.setWindowTitle("Edit Ticket" if ticket else "New Ticket")
        self.setFixedWidth(layout.DIALOG_WIDTH + 80)

        self._build_ui()
        if ticket:
            self._prefill_from_ticket(ticket)
        else:
            self._select_default_status()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds every field and wires up the customer -> device dependency."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.customer_combo = self._make_searchable_combo()
        for customer in self.reference_data["customers"]:
            label = f"{customer['first_name']} {customer['last_name']} ({customer['email']})"
            self.customer_combo.addItem(label, userData=customer["id"])
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)

        self.device_combo = QComboBox()
        self.device_combo.setFixedHeight(layout.INPUT_HEIGHT)

        self.category_combo = QComboBox()
        self.category_combo.setFixedHeight(layout.INPUT_HEIGHT)
        for category in self.reference_data["categories"]:
            self.category_combo.addItem(category["name"], userData=category["id"])

        self.type_combo = QComboBox()
        self.type_combo.setFixedHeight(layout.INPUT_HEIGHT)
        for ticket_type in self.reference_data["types"]:
            self.type_combo.addItem(ticket_type["name"], userData=ticket_type["id"])

        self.status_combo = QComboBox()
        self.status_combo.setFixedHeight(layout.INPUT_HEIGHT)
        for status in self.reference_data["statuses"]:
            self.status_combo.addItem(status["name"], userData=status["id"])

        self.priority_combo = QComboBox()
        self.priority_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.priority_combo.addItems(PRIORITY_LEVELS)

        self.assigned_to_combo = QComboBox()
        self.assigned_to_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self._populate_assigned_to()

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Short summary of the issue")
        self.title_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Details (optional)")
        self.description_input.setFixedHeight(100)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Ticket")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("Customer", self.customer_combo),
            ("Device", self.device_combo),
            ("Category", self.category_combo),
            ("Type", self.type_combo),
            ("Status", self.status_combo),
            ("Priority", self.priority_combo),
            ("Assigned To", self.assigned_to_combo),
            ("Title", self.title_input),
            ("Description", self.description_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)
        self._on_customer_changed()  # populate devices for whatever customer is initially selected

    def _make_searchable_combo(self) -> QComboBox:
        """
        Builds an editable QComboBox with type-ahead filtering, used for
        the customer picker since that list can grow large enough that a
        plain scrolling dropdown isn't practical.

        Returns:
            A QComboBox configured for search-as-you-type selection.
        """
        combo = QComboBox()
        combo.setFixedHeight(layout.INPUT_HEIGHT)
        combo.setEditable(True)
        combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = combo.completer()
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        return combo

    def _populate_assigned_to(self):
        """
        Fills the Assigned To dropdown with "Unassigned", "Me" (using the
        current user's own id -- no API call needed, works for any
        role), and the rest of the technician list if it was available
        (superuser sessions only; see TicketsDataWorker._load_users).
        """
        self.assigned_to_combo.addItem("Unassigned", userData=None)

        my_id = session.current_user_id()
        my_name = session.current_full_name() or "Me"
        if my_id is not None:
            self.assigned_to_combo.addItem(f"Me ({my_name})", userData=my_id)

        for user in self.reference_data.get("users", []):
            if user["id"] == my_id:
                continue  # already listed as "Me" above
            if not user.get("is_active", True):
                continue
            self.assigned_to_combo.addItem(user["full_name"], userData=user["id"])

    # -----------------------------------------------------------------
    # Customer -> device dependency
    # -----------------------------------------------------------------
    def _on_customer_changed(self):
        """
        Repopulates the device dropdown to only show devices belonging
        to the currently selected customer, since a device always
        belongs to exactly one customer.
        """
        self.device_combo.clear()
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            self.device_combo.setEnabled(False)
            return

        matching_devices = [
            d for d in self.reference_data["devices"] if d["customer_id"] == customer_id
        ]
        self.device_combo.setEnabled(bool(matching_devices))
        for device in matching_devices:
            parts = [device["device_type"]]
            if device.get("brand"):
                parts.append(device["brand"])
            if device.get("model"):
                parts.append(device["model"])
            label = " ".join(parts)
            if device.get("serial_number"):
                label += f" (SN: {device['serial_number']})"
            self.device_combo.addItem(label, userData=device["id"])

    # -----------------------------------------------------------------
    # Prefill (edit mode) / defaults (create mode)
    # -----------------------------------------------------------------
    def _select_default_status(self):
        """Pre-selects "Open" as the status for a newly created ticket, if it exists."""
        index = self.status_combo.findText(DEFAULT_STATUS_NAME)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)

    def _prefill_from_ticket(self, ticket: dict):
        """
        Populates every field from an existing ticket record, for edit mode.

        Args:
            ticket: The ticket dict being edited.
        """
        self._select_combo_by_data(self.customer_combo, ticket["customer_id"])
        self._on_customer_changed()  # repopulate devices for this ticket's customer first
        self._select_combo_by_data(self.device_combo, ticket["device_id"])
        self._select_combo_by_data(self.category_combo, ticket["category_id"])
        self._select_combo_by_data(self.type_combo, ticket["type_id"])
        self._select_combo_by_data(self.status_combo, ticket["status_id"])
        self._select_combo_by_data(self.assigned_to_combo, ticket.get("assigned_to"))

        priority_index = self.priority_combo.findText(ticket.get("priority", ""))
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        self.title_input.setText(ticket.get("title", ""))
        self.description_input.setPlainText(ticket.get("description") or "")

    def _select_combo_by_data(self, combo: QComboBox, data_value):
        """
        Selects the combo box item whose userData matches the given value.

        Args:
            combo: The combo box to update.
            data_value: The id to match against each item's userData.
        """
        index = combo.findData(data_value)
        if index >= 0:
            combo.setCurrentIndex(index)

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        payload, error = self._build_payload()
        if error:
            self._show_error(error)
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        ticket_id = self.ticket["id"] if self.ticket else None
        self._thread = QThread()
        self._worker = TicketSaveWorker(payload, ticket_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _build_payload(self) -> tuple[dict, str]:
        """
        Validates every required field and assembles the request payload.

        Returns:
            A (payload, error_message) tuple. error_message is empty if
            validation passed.
        """
        customer_id = self.customer_combo.currentData()
        device_id = self.device_combo.currentData()
        category_id = self.category_combo.currentData()
        type_id = self.type_combo.currentData()
        status_id = self.status_combo.currentData()
        title = self.title_input.text().strip()

        if customer_id is None:
            return {}, "Select a customer."
        if device_id is None:
            return {}, "Select a device for this customer."
        if category_id is None or type_id is None or status_id is None:
            return {}, "Select a category, type, and status."
        if not title:
            return {}, "Enter a title."

        payload = {
            "customer_id": customer_id,
            "device_id": device_id,
            "category_id": category_id,
            "type_id": type_id,
            "status_id": status_id,
            "priority": self.priority_combo.currentText(),
            "assigned_to": self.assigned_to_combo.currentData(),
            "title": title,
            "description": self.description_input.toPlainText().strip() or None,
        }
        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Handles the save worker's result. Closes the dialog on success,
        or re-enables the form and shows the error inline on failure.

        Args:
            success: Whether the save succeeded.
            result: The saved ticket record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Ticket")

        if not success:
            self._show_error(result)
            return

        self.saved_ticket = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
