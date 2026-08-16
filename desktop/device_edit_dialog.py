# ER-ServiceDesk/desktop/device_edit_dialog.py

"""
Dialog for editing an existing device's details.

Edit-only -- there's no "New Device" path here. A device's first real
appearance in the system is ticket intake (see ticket_form_dialog.py's
"+ Add New Device"); this dialog exists purely to fix a typo'd serial
number or correct a brand/model after the fact, reached by double-
clicking a device in a customer's device list.
"""

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QCompleter,
    QDialog,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.device_save_worker import DeviceSaveWorker
from desktop.device_user_account_dialog import DeviceUserAccountDialog


class DeviceEditDialog(QDialog):
    """
    Modal dialog for editing an existing device.

    On a successful save, the dialog closes itself and the saved device
    record is available via `self.saved_device`.
    """

    def __init__(self, device: dict, locations: list[dict], all_customers: list[dict], parent=None):
        """
        Args:
            device: The existing device dict to edit.
            locations: The full locations list, for the Location dropdown.
            all_customers: Every customer in the system, for the
                reassignment picker -- moving a device to the correct
                customer record (e.g. cleaning up a duplicate) means
                picking from the full list, not just the one this
                dialog was opened from.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.device = device
        self.locations = locations
        self.all_customers = all_customers
        self.saved_device: dict | None = None
        self.deleted = False

        self._thread: QThread | None = None
        self._worker: DeviceSaveWorker | None = None

        self.setWindowTitle("Edit Device")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "DeviceEditDialog")

        self._build_ui()
        self._prefill_from_device(device)

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "DeviceEditDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds every field."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.device_type_input = QLineEdit()
        self.device_type_input.setPlaceholderText("Device type, e.g. Laptop (required)")
        self.device_type_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.brand_input = QLineEdit()
        self.brand_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.model_input = QLineEdit()
        self.model_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.serial_number_input = QLineEdit()
        self.serial_number_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.os_input = QLineEdit()
        self.os_input.setPlaceholderText("e.g. Windows 11 (optional)")
        self.os_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.edition_input = QLineEdit()
        self.edition_input.setPlaceholderText("e.g. Home, Pro, Enterprise (optional)")
        self.edition_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.location_combo = QComboBox()
        self.location_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.location_combo.addItem("-- None --", userData=None)
        for location in self.locations:
            self.location_combo.addItem(location["name"], userData=location["id"])

        self.customer_combo = QComboBox()
        self.customer_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.customer_combo.setEditable(True)
        self.customer_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        completer = self.customer_combo.completer()
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        current_customer_id = self.device.get("customer_id")
        for customer in self.all_customers:
            # Archived customers are hidden from the picker for NEW
            # selections, same reasoning as the ticket form's own
            # customer picker -- the one exception is the device's
            # current owner, so the dropdown correctly reflects who
            # it's actually assigned to even if that customer's since
            # been archived, rather than showing nothing.
            if customer.get("is_archived") and customer["id"] != current_customer_id:
                continue
            label = f"{customer['first_name']} {customer['last_name']} ({customer['email']})"
            self.customer_combo.addItem(label, userData=customer["id"])

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Device")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        self.delete_button = QPushButton("Delete Device")
        self.delete_button.setObjectName("danger")
        self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.delete_button.clicked.connect(self._attempt_delete)

        for label_text, widget in [
            ("Owner", self.customer_combo),
            ("Device Type", self.device_type_input),
            ("Brand", self.brand_input),
            ("Model", self.model_input),
            ("Serial Number", self.serial_number_input),
            ("OS", self.os_input),
            ("Edition", self.edition_input),
            ("Current Location", self.location_combo),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self._build_user_accounts_section())

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)

    def _prefill_from_device(self, device: dict):
        """
        Args:
            device: The device dict being edited.
        """
        customer_index = self.customer_combo.findData(device.get("customer_id"))
        if customer_index >= 0:
            self.customer_combo.setCurrentIndex(customer_index)

        self.device_type_input.setText(device.get("device_type", ""))
        self.brand_input.setText(device.get("brand") or "")
        self.model_input.setText(device.get("model") or "")
        self.serial_number_input.setText(device.get("serial_number") or "")
        self.os_input.setText(device.get("os") or "")
        self.edition_input.setText(device.get("edition") or "")

        index = self.location_combo.findData(device.get("current_location_id"))
        if index >= 0:
            self.location_combo.setCurrentIndex(index)

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread. Confirms first if the owner is actually being changed -- reassigning a device is a real, meaningful action, not a routine edit."""
        payload, error = self._build_payload()
        if error:
            self._show_error(error)
            return

        if payload["customer_id"] != self.device.get("customer_id"):
            new_owner_label = self.customer_combo.currentText()
            confirmed = QMessageBox.question(
                self,
                "Reassign Device",
                f"Reassign this device to {new_owner_label}? It will no longer show up under its current customer's device list.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if confirmed != QMessageBox.StandardButton.Yes:
                return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        self._thread = QThread()
        self._worker = DeviceSaveWorker(self.device["id"], payload)
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
        device_type = self.device_type_input.text().strip()
        if not device_type:
            return {}, "Enter a device type."

        customer_id = self.customer_combo.currentData()
        if customer_id is None:
            return {}, "Select an owner."

        payload = {
            "customer_id": customer_id,
            "device_type": device_type,
            "brand": self.brand_input.text().strip() or None,
            "model": self.model_input.text().strip() or None,
            "serial_number": self.serial_number_input.text().strip() or None,
            "os": self.os_input.text().strip() or None,
            "edition": self.edition_input.text().strip() or None,
            "current_location_id": self.location_combo.currentData(),
        }
        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            success: Whether the save succeeded.
            result: The saved device record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Device")

        if not success:
            self._show_error(result)
            return

        self.saved_device = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()

    # -----------------------------------------------------------------
    # User Accounts
    # -----------------------------------------------------------------
    def _build_user_accounts_section(self) -> QWidget:
        """
        Builds the expandable user-accounts table for this device --
        supports more than one login (the rare-but-real multi-account
        case), each tracked separately with its own admin flag and
        encrypted password. Always shown -- this dialog is edit-only,
        so self.device always has a real id.

        Returns:
            The assembled section widget (label + Add button + table),
            ready to add to the form's layout.
        """
        section_label = QLabel("User Accounts")
        section_label.setObjectName("subtitle")

        add_account_button = QPushButton("Add User Account")
        add_account_button.setObjectName("secondary")
        add_account_button.clicked.connect(self._on_add_user_account)

        self.accounts_table = QTableWidget()
        self.accounts_table.setColumnCount(2)
        self.accounts_table.setHorizontalHeaderLabels(["Account", "Admin"])
        self.accounts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.accounts_table.verticalHeader().setVisible(False)
        self.accounts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.accounts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.accounts_table.setFixedHeight(120)
        self.accounts_table.doubleClicked.connect(self._on_account_row_double_clicked)

        self._load_user_accounts()

        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(section_label)
        container_layout.addWidget(add_account_button)
        container_layout.addWidget(self.accounts_table)
        container = QWidget()
        container.setLayout(container_layout)
        return container

    def _load_user_accounts(self):
        """Fetches and renders this device's current user accounts."""
        try:
            accounts = api_client.list_device_user_accounts(self.device["id"])
        except ApiError:
            accounts = []

        self.accounts_table.setRowCount(len(accounts))
        for row, account in enumerate(accounts):
            values = [account.get("account_name", ""), "Yes" if account.get("is_admin") else "No"]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, account)
                self.accounts_table.setItem(row, col, item)

    def _on_add_user_account(self):
        """Opens DeviceUserAccountDialog in add mode; refreshes the table if an account was added."""
        dialog = DeviceUserAccountDialog(self.device["id"], None, parent=self)
        if dialog.exec():
            self._load_user_accounts()

    def _on_account_row_double_clicked(self):
        """Opens DeviceUserAccountDialog pre-filled with the double-clicked row's account; refreshes the table if saved or removed."""
        selected_items = self.accounts_table.selectedItems()
        if not selected_items:
            return

        account = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = DeviceUserAccountDialog(self.device["id"], account, parent=self)
        if dialog.exec():
            self._load_user_accounts()

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete(self):
        """
        Confirms, then deletes this device. Synchronous (no QThread) --
        this is a small, infrequent action, not performance-critical.
        Shows the real backend reason inline if blocked (e.g. still
        attached to a ticket) rather than a generic failure message.
        """
        confirmed = QMessageBox.question(
            self,
            "Delete Device",
            "Delete this device? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)
        try:
            api_client.delete_device(self.device["id"])
        except ApiError as e:
            self._show_error(str(e))
            return
        finally:
            self.delete_button.setEnabled(True)

        self.deleted = True
        self.accept()
