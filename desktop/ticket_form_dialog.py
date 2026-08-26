# ER-ServiceDesk/desktop/ticket_form_dialog.py

"""
Dialog for creating a new ticket or editing an existing one.

Every foreign-keyed field (customer, device, category, type, status,
assigned technician) is a dropdown populated from the backend -- never
free text -- so a ticket can never reference a category or status that
doesn't actually exist. Customer uses a searchable/type-ahead combo box
since that list can grow large; everything else is a small fixed list,
so a plain dropdown is enough. Priority is a fixed four-level list (Low/Medium/High/Urgent) rather
than a backend lookup table -- its real-world vocabulary is small and
stable, the same reasoning behind Asset's fixed Status/Condition lists.

Assigned To always offers "Unassigned" and "Me" (self-assignment), using
the current user's own id from their JWT claims -- no API call needed,
and it works regardless of role. The full list of other assignable
users is available to every role now (see api_client.list_assignable_
users()), excluding anyone with the front_desk role -- front desk can
assign tickets to agents, but should never be an assignment target
themselves.

The device dropdown always includes a "+ Add New Device" option, since
intake in practice usually means a device is seeing the system for the
first time -- requiring it to already exist would block ticket creation
for most real customers. Choosing it reveals inline fields; the device
is created as part of the same save as the ticket (see TicketSaveWorker).
"""

from PySide6.QtCore import QThread, Qt
import traceback
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout, session
from desktop.api_client import ApiError
from desktop.base_dialog import AppDialog
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.ticket_save_worker import TicketSaveWorker
from desktop.notes_dialog import NotesDialog
from desktop.billing_dialog import BillingDialog
from desktop.ticket_history_dialog import TicketHistoryDialog
from desktop.ticket_part_dialog import TicketPartDialog

PRIORITY_LEVELS = ["Low", "Medium", "High", "Urgent"]
DEFAULT_STATUS_NAME = "Open"
NEW_DEVICE_SENTINEL = "__new_device__"


class TicketFormDialog(AppDialog):
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
                lists loaded by TicketsDataWorker. "users" now includes
                every active user for every role (id/full_name/
                is_front_desk); see api_client.list_assignable_users().
        """
        super().__init__(parent)
        self.reference_data = reference_data
        self.ticket = ticket
        self.saved_ticket: dict | None = None

        self._thread: QThread | None = None
        self._worker: TicketSaveWorker | None = None

        self.setWindowTitle("Edit Ticket" if ticket else "New Ticket")
        self.setMinimumWidth(layout.DIALOG_WIDTH + 80)
        self.resize(layout.DIALOG_WIDTH + 80, 600)
        restore_geometry(self, "TicketFormDialog")

        self._build_ui()
        if ticket:
            self._prefill_from_ticket(ticket)
        else:
            self._select_default_status()

    def closeEvent(self, event):
        save_geometry(self, "TicketFormDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """
        Builds every field and wires up the customer -> device
        dependency. Fields live inside a scroll area (this dialog has
        enough fields that its natural unscrolled height, ~860px,
        exceeds many laptop screens) -- Save/Cancel and the error
        message stay pinned outside it, always reachable regardless of
        scroll position or window height.
        """
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        content_layout.setSpacing(layout.SPACE_SM)

        self.customer_combo = self._make_searchable_combo()
        current_customer_id = self.ticket.get("customer_id") if self.ticket else None
        for customer in self.reference_data["customers"]:
            # Archived customers are hidden from the picker for NEW
            # selections -- per design, only active customers should
            # be assignable to a ticket. The one exception: if this
            # ticket is already assigned to a customer who's since
            # been archived, that customer still needs to appear here
            # so the dropdown correctly reflects who the ticket is
            # actually assigned to, rather than showing nothing.
            if customer.get("is_archived") and customer["id"] != current_customer_id:
                continue
            label = f"{customer['first_name']} {customer['last_name']} ({customer['email']})"
            self.customer_combo.addItem(label, userData=customer["id"])
        self.customer_combo.currentIndexChanged.connect(self._on_customer_changed)

        self.device_combo = QComboBox()
        self.device_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.device_combo.currentIndexChanged.connect(self._on_device_selection_changed)

        self.new_device_type_input = QLineEdit()
        self.new_device_type_input.setPlaceholderText("Device type, e.g. Laptop (required)")
        self.new_device_type_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.new_device_brand_input = QLineEdit()
        self.new_device_brand_input.setPlaceholderText("Brand (optional)")
        self.new_device_brand_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.new_device_model_input = QLineEdit()
        self.new_device_model_input.setPlaceholderText("Model (optional)")
        self.new_device_model_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.new_device_serial_input = QLineEdit()
        self.new_device_serial_input.setPlaceholderText("Serial number (optional)")
        self.new_device_serial_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.new_device_fields = [
            self.new_device_type_input,
            self.new_device_brand_input,
            self.new_device_model_input,
            self.new_device_serial_input,
        ]
        for field in self.new_device_fields:
            field.hide()

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

        self.location_combo = QComboBox()
        self.location_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.location_combo.addItem("-- None --", userData=None)
        current_location_id = self.ticket.get("current_location_id") if self.ticket else None
        for location in self.reference_data.get("locations", []):
            if location.get("show_in_ticket_picker", True) or location["id"] == current_location_id:
                self.location_combo.addItem(location["name"], userData=location["id"])

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Short summary of the issue")
        self.title_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Details (optional)")
        self.description_input.setFixedHeight(100)

        self.pickup_person_input = QLineEdit()
        self.pickup_person_input.setPlaceholderText("Who is authorized to pick up the device (optional)")
        self.pickup_person_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.accessories_included_input = QLineEdit()
        self.accessories_included_input.setPlaceholderText("What was brought in, e.g. charger, bag (optional)")
        self.accessories_included_input.setFixedHeight(layout.INPUT_HEIGHT)

        # Only shown when editing an EXISTING ticket -- a brand-new,
        # unsaved ticket has no id yet for a part requirement to
        # attach to, matching the same reasoning as Notes/History.
        parts_section = None
        if self.ticket:
            parts_section = self._build_parts_section()

        for label_text, widget in [
            ("Customer", self.customer_combo),
            ("Device", self.device_combo),
            (None, self.new_device_type_input),
            (None, self.new_device_brand_input),
            (None, self.new_device_model_input),
            (None, self.new_device_serial_input),
            ("Category", self.category_combo),
            ("Type", self.type_combo),
            ("Status", self.status_combo),
            ("Priority", self.priority_combo),
            ("Assigned To", self.assigned_to_combo),
            ("Location", self.location_combo),
            ("Title", self.title_input),
            ("Description", self.description_input),
            ("Pick Up Person", self.pickup_person_input),
            ("Accessories Included", self.accessories_included_input),
        ]:
            if label_text is not None:
                field_label = QLabel(label_text)
                field_label.setObjectName("subtitle")
                content_layout.addWidget(field_label)
            content_layout.addWidget(widget)

        if parts_section is not None:
            content_layout.addWidget(parts_section)

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area)

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

        # Only shown when editing an EXISTING ticket -- a brand-new,
        # unsaved ticket has no id yet for a note to attach to. Once
        # the ticket's been saved once and reopened, notes become
        # available.
        notes_button = None
        history_button = None
        billing_button = None
        waiver_button = None
        if self.ticket:
            notes_button = QPushButton("Notes")
            notes_button.setObjectName("secondary")
            notes_button.setFixedHeight(layout.BUTTON_HEIGHT)
            notes_button.clicked.connect(self._open_notes_dialog)

            history_button = QPushButton("History")
            history_button.setObjectName("secondary")
            history_button.setFixedHeight(layout.BUTTON_HEIGHT)
            history_button.clicked.connect(self._open_history_dialog)

            billing_button = QPushButton("Billing")
            billing_button.setObjectName("secondary")
            billing_button.setFixedHeight(layout.BUTTON_HEIGHT)
            billing_button.clicked.connect(self._open_billing_dialog)

            waiver_button = QPushButton("Send Waiver")
            waiver_button.setObjectName("secondary")
            waiver_button.setFixedHeight(layout.BUTTON_HEIGHT)
            waiver_button.clicked.connect(self._on_send_waiver)

        bottom_bar = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.SPACE_SM,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        bottom_layout.setSpacing(layout.SPACE_SM)
        bottom_layout.addWidget(self.error_label)
        bottom_layout.addWidget(self.save_button)
        if notes_button:
            bottom_layout.addWidget(notes_button)
        if history_button:
            bottom_layout.addWidget(history_button)
        if billing_button:
            bottom_layout.addWidget(billing_button)
        if waiver_button:
            bottom_layout.addWidget(waiver_button)
            self.waiver_status_label = QLabel(self._format_waiver_status())
            self.waiver_status_label.setObjectName("subtitle")
            bottom_layout.addWidget(self.waiver_status_label)
        bottom_layout.addWidget(cancel_button)
        bottom_bar.setLayout(bottom_layout)
        outer_layout.addWidget(bottom_bar)

        self.setLayout(outer_layout)
        self._on_customer_changed()  # populate devices for whatever customer is initially selected

    def _open_notes_dialog(self):
        """
        Opens the note history + composer for this ticket. Only ever
        called when self.ticket is set (the Notes button doesn't
        exist otherwise).

        Modal (exec, not show) -- mixing a modal parent (this ticket
        form, shown via its own .exec() from LockGate) with a
        non-modal child can create real, platform-specific
        input-routing behavior; modal removes that whole category of
        risk.

        NotesDialog itself stays fully synchronous (no QThread).
        """
        try:
            self._notes_dialog = NotesDialog(self.ticket["id"], self.ticket.get("title", "Ticket"), self.ticket.get("customer_id"), parent=self)
            self._notes_dialog.exec()
        except Exception:
            # This app's console=False build has no way to surface an
            # uncaught exception at all -- it just silently terminates.
            # Catching and displaying it here is a genuine safety net.
            QMessageBox.critical(self, "Notes Error", traceback.format_exc())

    def _open_history_dialog(self):
        """
        Opens this ticket's full history -- status changes and general
        activity, merged into one timeline. Only ever called when
        self.ticket is set (the History button doesn't exist
        otherwise). Modal, same reasoning as Notes (see
        _open_notes_dialog's own docstring).
        """
        try:
            dialog = TicketHistoryDialog(self.ticket["id"], self.ticket.get("title", "Ticket"), parent=self)
            dialog.exec()
        except Exception:
            QMessageBox.critical(self, "History Error", traceback.format_exc())

    def _open_billing_dialog(self):
        """
        Opens this ticket's billing screen -- every quote and invoice
        for it. Only ever called when self.ticket is set (the Billing
        button doesn't exist otherwise). Modal, same reasoning as
        Notes (see _open_notes_dialog's own docstring).
        """
        try:
            dialog = BillingDialog(self.ticket["id"], self.ticket.get("title", "Ticket"), parent=self)
            dialog.exec()
        except Exception:
            QMessageBox.critical(self, "Billing Error", traceback.format_exc())

    def _format_waiver_status(self) -> str:
        """
        Returns:
            "Waiver sent on YYYY-MM-DD." if it's ever been sent, or a
            plain "not yet sent" message otherwise. Only ever called
            when self.ticket is set (the waiver button doesn't exist
            otherwise).
        """
        sent_at = self.ticket.get("waiver_sent_at")
        if sent_at:
            return f"Waiver sent on {sent_at[:10]}."
        return "Waiver not yet sent."

    def _on_send_waiver(self):
        """
        Confirms, then emails the liability waiver to this ticket's
        customer -- email-only, no print/signature path. Only ever
        called when self.ticket is set (the waiver button doesn't
        exist otherwise).
        """
        confirmed = QMessageBox.question(
            self,
            "Send Liability Waiver",
            "Email the liability waiver to this customer? Their reply will come back as a note on this ticket, same as any other customer email.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        try:
            updated_ticket = api_client.send_waiver(self.ticket["id"])
        except ApiError as e:
            self.handle_api_error(e, title="Send Failed")
            return

        self.ticket = updated_ticket
        self.waiver_status_label.setText(self._format_waiver_status())

    def _build_parts_section(self) -> QWidget:
        """
        Builds the expandable parts-needed table for this ticket --
        supports multiple parts on one ticket (e.g. a repair needing
        both a screen and a battery), each tracked separately with its
        own status. Only ever built when self.ticket is set.

        Returns:
            The assembled parts section widget (label + Add button +
            table), ready to add to the form's content layout.
        """
        section_label = QLabel("Parts Needed")
        section_label.setObjectName("subtitle")

        add_part_button = QPushButton("Add Part")
        add_part_button.setObjectName("secondary")
        add_part_button.clicked.connect(self._on_add_part)

        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(3)
        self.parts_table.setHorizontalHeaderLabels(["Part", "Qty", "Status"])
        self.parts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.parts_table.verticalHeader().setVisible(False)
        self.parts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.parts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.parts_table.setFixedHeight(120)
        self.parts_table.doubleClicked.connect(self._on_part_row_double_clicked)

        self._load_parts_table()

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(section_label)
        container_layout.addWidget(add_part_button)
        container_layout.addWidget(self.parts_table)
        container = QWidget()
        container.setLayout(container_layout)
        return container

    def _load_parts_table(self):
        """Fetches and renders this ticket's current part requirements."""
        try:
            self._ticket_parts = api_client.list_ticket_parts_for_ticket(self.ticket["id"])
        except ApiError:
            self._ticket_parts = []

        part_names_by_id = {p["id"]: p.get("name", "") for p in self.reference_data.get("parts", [])}

        self.parts_table.setRowCount(len(self._ticket_parts))
        for row, ticket_part in enumerate(self._ticket_parts):
            values = [
                part_names_by_id.get(ticket_part.get("part_id"), "Unknown"),
                str(ticket_part.get("quantity_needed", 1)),
                (ticket_part.get("status") or "needed").capitalize(),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, ticket_part)
                self.parts_table.setItem(row, col, item)

    def _on_add_part(self):
        """Opens TicketPartDialog in create mode; refreshes the table if a part was added."""
        dialog = TicketPartDialog(self.ticket["id"], self.reference_data.get("parts", []), None, parent=self)
        if dialog.exec():
            self._load_parts_table()

    def _on_part_row_double_clicked(self):
        """Opens TicketPartDialog pre-filled with the double-clicked row's part; refreshes the table if saved or removed."""
        selected_items = self.parts_table.selectedItems()
        if not selected_items:
            return

        ticket_part = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = TicketPartDialog(self.ticket["id"], self.reference_data.get("parts", []), ticket_part, parent=self)
        if dialog.exec():
            self._load_parts_table()

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
        Fills the Assigned To dropdown with "Unassigned", "Me" (unless
        the current user is themselves front desk -- see below), and
        every other assignable user, excluding anyone with the
        front_desk role entirely. Front desk can assign tickets to
        agents, but should never be an assignment target themselves,
        since they work the front desk rather than tickets directly.
        """
        self.assigned_to_combo.addItem("Unassigned", userData=None)

        my_id = session.current_user_id()
        my_name = session.current_full_name() or "Me"
        i_am_front_desk = any(
            user["id"] == my_id and user.get("is_front_desk")
            for user in self.reference_data.get("users", [])
        )
        i_am_currently_assigned = self.ticket is not None and self.ticket.get("assigned_to") == my_id
        if my_id is not None and (not i_am_front_desk or i_am_currently_assigned):
            self.assigned_to_combo.addItem(f"Me ({my_name})", userData=my_id)

        for user in self.reference_data.get("users", []):
            if user["id"] == my_id:
                continue  # already listed as "Me" above, or correctly excluded if front desk
            currently_assigned = self.ticket is not None and self.ticket.get("assigned_to") == user["id"]
            if user.get("is_front_desk") and not currently_assigned:
                continue
            self.assigned_to_combo.addItem(user["full_name"], userData=user["id"])

    # -----------------------------------------------------------------
    # Customer -> device dependency
    # -----------------------------------------------------------------
    def _on_customer_changed(self):
        """
        Repopulates the device dropdown to only show devices belonging
        to the currently selected customer, since a device always
        belongs to exactly one customer. The "+ Add New Device" option
        is always available, even when the customer has no devices on
        file yet -- which is true for most real customers right now.
        """
        self.device_combo.clear()
        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            self.device_combo.setEnabled(False)
            return

        matching_devices = [
            d for d in self.reference_data["devices"] if d["customer_id"] == customer_id
        ]
        self.device_combo.setEnabled(True)
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
        self.device_combo.addItem("+ Add New Device", userData=NEW_DEVICE_SENTINEL)

    def _on_device_selection_changed(self):
        """Shows the inline new-device fields only when "+ Add New Device" is selected."""
        is_new_device = self.device_combo.currentData() == NEW_DEVICE_SENTINEL
        for field in self.new_device_fields:
            field.setVisible(is_new_device)

    # -----------------------------------------------------------------
    # Prefill (edit mode) / defaults (create mode)
    # -----------------------------------------------------------------
    def _select_default_status(self):
        """Pre-selects "Open" as the status for a newly created ticket, if it exists."""
        index = self.status_combo.findText(DEFAULT_STATUS_NAME)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)

    def _prefill_from_ticket(self, ticket: dict):
        """Populates every field from an existing ticket record, for edit mode."""
        self._select_combo_by_data(self.customer_combo, ticket["customer_id"])
        self._on_customer_changed()  # repopulate devices for this ticket's customer first
        self._select_combo_by_data(self.device_combo, ticket["device_id"])
        self._select_combo_by_data(self.category_combo, ticket["category_id"])
        self._select_combo_by_data(self.type_combo, ticket["type_id"])
        self._select_combo_by_data(self.status_combo, ticket["status_id"])
        self._select_combo_by_data(self.assigned_to_combo, ticket.get("assigned_to"))
        self._select_combo_by_data(self.location_combo, ticket.get("current_location_id"))

        priority_index = self.priority_combo.findText(ticket.get("priority", ""))
        if priority_index >= 0:
            self.priority_combo.setCurrentIndex(priority_index)

        self.title_input.setText(ticket.get("title", ""))
        self.description_input.setPlainText(ticket.get("description") or "")
        self.pickup_person_input.setText(ticket.get("pickup_person") or "")
        self.accessories_included_input.setText(ticket.get("accessories_included") or "")

    def _select_combo_by_data(self, combo: QComboBox, data_value):
        index = combo.findData(data_value)
        if index >= 0:
            combo.setCurrentIndex(index)

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        payload, new_device_payload, error = self._build_payload()
        if error:
            self._show_error(error)
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        ticket_id = self.ticket["id"] if self.ticket else None
        self._thread = QThread()
        self._worker = TicketSaveWorker(payload, ticket_id, new_device_payload)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _build_payload(self) -> tuple[dict, dict | None, str]:
        """
        Validates every required field and assembles the request
        payload(s). If "+ Add New Device" was selected, that device's
        fields are validated too and returned as a separate payload for
        TicketSaveWorker to create before the ticket itself.

        Returns:
            A (payload, new_device_payload, error_message) tuple.
            new_device_payload is None unless a new device is being
            created. error_message is empty if validation passed.
        """
        customer_id = self.customer_combo.currentData()
        device_id = self.device_combo.currentData()
        category_id = self.category_combo.currentData()
        type_id = self.type_combo.currentData()
        status_id = self.status_combo.currentData()
        title = self.title_input.text().strip()

        if customer_id is None:
            return {}, None, "Select a customer."
        if device_id is None:
            return {}, None, "Select a device for this customer."
        if category_id is None or type_id is None or status_id is None:
            return {}, None, "Select a category, type, and status."
        if not title:
            return {}, None, "Enter a title."

        new_device_payload = None
        if device_id == NEW_DEVICE_SENTINEL:
            device_type = self.new_device_type_input.text().strip()
            if not device_type:
                return {}, None, "Enter a device type for the new device."
            new_device_payload = {
                "customer_id": customer_id,
                "device_type": device_type,
                "brand": self.new_device_brand_input.text().strip() or None,
                "model": self.new_device_model_input.text().strip() or None,
                "serial_number": self.new_device_serial_input.text().strip() or None,
            }
            device_id = None  # filled in by TicketSaveWorker once the device is created

        payload = {
            "customer_id": customer_id,
            "device_id": device_id,
            "category_id": category_id,
            "type_id": type_id,
            "status_id": status_id,
            "priority": self.priority_combo.currentText(),
            "assigned_to": self.assigned_to_combo.currentData(),
            "current_location_id": self.location_combo.currentData(),
            "title": title,
            "description": self.description_input.toPlainText().strip() or None,
            "pickup_person": self.pickup_person_input.text().strip() or None,
            "accessories_included": self.accessories_included_input.text().strip() or None,
        }
        return payload, new_device_payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Handles the save worker's result. Closes the dialog on success,
        or re-enables the form and shows the error inline on failure.

        Args:
            result: The saved ticket record on success, or the caught
                ApiError on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Ticket")

        if not success:
            self.handle_api_error(result, on_other_error=self._show_error)
            return

        self.saved_ticket = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
