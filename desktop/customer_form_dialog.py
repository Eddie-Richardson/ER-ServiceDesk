# ER-ServiceDesk/desktop/customer_form_dialog.py

"""
Dialog for creating a new customer or editing an existing one.

In edit mode, shows the customer's devices below the form fields --
devices link directly to customer_id, so this listing is reliable
regardless of ticket history, not something derived from tickets. A new
customer has no devices yet, so that section only appears when editing
an existing one. Double-clicking a device opens DeviceEditDialog;
there's no "add a device here" button -- devices are only ever created
during ticket intake, per the earlier design decision.
"""

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.customer_save_worker import CustomerSaveWorker
from desktop.device_edit_dialog import DeviceEditDialog

DEVICE_COLUMN_HEADERS = ["Type", "Brand", "Model", "Serial Number"]


class CustomerFormDialog(QDialog):
    """
    Modal dialog for creating or editing a customer.

    Pass `customer=None` to create a new customer, or an existing
    customer dict to edit one. On a successful save, the dialog closes
    itself and the saved customer record is available via
    `self.saved_customer`.
    """

    def __init__(self, customer: dict | None, all_devices: list[dict], locations: list[dict], parent=None):
        """
        Args:
            customer: An existing customer dict to edit, or None to
                create a new one.
            all_devices: Every device in the system; filtered down to
                this customer's own devices for the sub-table.
            locations: The full locations list, passed through to
                DeviceEditDialog for its Location dropdown.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.customer = customer
        self.all_devices = all_devices
        self.locations = locations
        self.saved_customer: dict | None = None

        self._thread: QThread | None = None
        self._worker: CustomerSaveWorker | None = None

        self.setWindowTitle("Edit Customer" if customer else "New Customer")
        self.setFixedWidth(layout.DIALOG_WIDTH + 80)

        self._build_ui()
        if customer:
            self._prefill_from_customer(customer)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds the customer fields, and the devices sub-table if editing."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("First name (required)")
        self.first_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Last name (required)")
        self.last_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (required)")
        self.email_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.phone_input = QLineEdit()
        self.phone_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.address_input = QLineEdit()
        self.address_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Customer")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("First Name", self.first_name_input),
            ("Last Name", self.last_name_input),
            ("Email", self.email_input),
            ("Phone", self.phone_input),
            ("Address", self.address_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        if self.customer:
            outer_layout.addWidget(self._build_devices_section())

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)

    def _build_devices_section(self) -> QTableWidget:
        """
        Builds the read-only-at-a-glance devices table for this
        customer, populated from self.all_devices filtered by
        customer_id. Double-clicking a row opens DeviceEditDialog.

        Returns:
            The assembled devices QTableWidget.
        """
        devices_label = QLabel("Devices")
        devices_label.setObjectName("subtitle")

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(len(DEVICE_COLUMN_HEADERS))
        self.devices_table.setHorizontalHeaderLabels(DEVICE_COLUMN_HEADERS)
        self.devices_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.devices_table.verticalHeader().setVisible(False)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.devices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.devices_table.setFixedHeight(140)
        self.devices_table.doubleClicked.connect(self._on_device_row_double_clicked)

        self._populate_devices_table()

        # devices_label isn't returned, so wrap both in a container instead
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(devices_label)
        container_layout.addWidget(self.devices_table)
        container = QWidget()
        container.setLayout(container_layout)
        return container

    def _populate_devices_table(self):
        """Fills the devices table with this customer's devices, most-recent-looking first."""
        customer_id = self.customer["id"]
        my_devices = [d for d in self.all_devices if d["customer_id"] == customer_id]

        self.devices_table.setRowCount(len(my_devices))
        for row, device in enumerate(my_devices):
            values = [
                device.get("device_type", ""),
                device.get("brand") or "-",
                device.get("model") or "-",
                device.get("serial_number") or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, device)
                self.devices_table.setItem(row, col, item)

    def _on_device_row_double_clicked(self):
        """Opens DeviceEditDialog for the double-clicked device; refreshes the table if saved."""
        selected_items = self.devices_table.selectedItems()
        if not selected_items:
            return

        device = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = DeviceEditDialog(device, self.locations, parent=self)
        if dialog.exec():
            # Update our in-memory copy so the table reflects the edit
            # immediately, without needing to reload the whole window.
            for i, d in enumerate(self.all_devices):
                if d["id"] == dialog.saved_device["id"]:
                    self.all_devices[i] = dialog.saved_device
                    break
            self._populate_devices_table()

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_customer(self, customer: dict):
        """
        Args:
            customer: The customer dict being edited.
        """
        self.first_name_input.setText(customer.get("first_name", ""))
        self.last_name_input.setText(customer.get("last_name", ""))
        self.email_input.setText(customer.get("email", ""))
        self.phone_input.setText(customer.get("phone") or "")
        self.address_input.setText(customer.get("address") or "")

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

        customer_id = self.customer["id"] if self.customer else None
        self._thread = QThread()
        self._worker = CustomerSaveWorker(payload, customer_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _build_payload(self) -> tuple[dict, str]:
        """
        Returns:
            A (payload, error_message) tuple. error_message is empty if
            validation passed.
        """
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        email = self.email_input.text().strip()

        if not first_name or not last_name:
            return {}, "Enter both a first and last name."
        if not email:
            return {}, "Enter an email address."

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
        }
        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            success: Whether the save succeeded.
            result: The saved customer record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Customer")

        if not success:
            self._show_error(result)
            return

        self.saved_customer = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
