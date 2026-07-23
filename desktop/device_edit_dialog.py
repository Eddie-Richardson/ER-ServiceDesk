# ER-ServiceDesk/desktop/device_edit_dialog.py

"""
Dialog for editing an existing device's details.

Edit-only -- there's no "New Device" path here. A device's first real
appearance in the system is ticket intake (see ticket_form_dialog.py's
"+ Add New Device"); this dialog exists purely to fix a typo'd serial
number or correct a brand/model after the fact, reached by double-
clicking a device in a customer's device list.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from desktop import layout
from desktop.device_save_worker import DeviceSaveWorker


class DeviceEditDialog(QDialog):
    """
    Modal dialog for editing an existing device.

    On a successful save, the dialog closes itself and the saved device
    record is available via `self.saved_device`.
    """

    def __init__(self, device: dict, locations: list[dict], parent=None):
        """
        Args:
            device: The existing device dict to edit.
            locations: The full locations list, for the Location dropdown.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.device = device
        self.locations = locations
        self.saved_device: dict | None = None

        self._thread: QThread | None = None
        self._worker: DeviceSaveWorker | None = None

        self.setWindowTitle("Edit Device")
        self.setFixedWidth(layout.DIALOG_WIDTH)

        self._build_ui()
        self._prefill_from_device(device)

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

        self.location_combo = QComboBox()
        self.location_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.location_combo.addItem("-- None --", userData=None)
        for location in self.locations:
            self.location_combo.addItem(location["name"], userData=location["id"])

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

        for label_text, widget in [
            ("Device Type", self.device_type_input),
            ("Brand", self.brand_input),
            ("Model", self.model_input),
            ("Serial Number", self.serial_number_input),
            ("Current Location", self.location_combo),
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

    def _prefill_from_device(self, device: dict):
        """
        Args:
            device: The device dict being edited.
        """
        self.device_type_input.setText(device.get("device_type", ""))
        self.brand_input.setText(device.get("brand") or "")
        self.model_input.setText(device.get("model") or "")
        self.serial_number_input.setText(device.get("serial_number") or "")

        index = self.location_combo.findData(device.get("current_location_id"))
        if index >= 0:
            self.location_combo.setCurrentIndex(index)

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

        payload = {
            "device_type": device_type,
            "brand": self.brand_input.text().strip() or None,
            "model": self.model_input.text().strip() or None,
            "serial_number": self.serial_number_input.text().strip() or None,
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
