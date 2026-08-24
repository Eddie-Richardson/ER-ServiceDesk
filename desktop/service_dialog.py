# ER-ServiceDesk/desktop/service_dialog.py

"""
Dialog for creating a new billable service or editing an existing one.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from desktop import layout
from desktop.base_dialog import AppDialog
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.lookup_save_worker import LookupSaveWorker

ENDPOINT = "/services/"


class ServiceDialog(AppDialog):
    """
    Modal dialog for creating or editing a billable service.

    Pass `service=None` to create a new one, or an existing service
    dict to edit it. On a successful save, the dialog closes itself
    and the saved record is available via `self.saved_service`.
    """

    def __init__(self, service: dict | None = None, parent=None):
        super().__init__(parent)
        self.service = service
        self.saved_service: dict | None = None

        self._thread: QThread | None = None
        self._worker: LookupSaveWorker | None = None

        self.setWindowTitle("Edit Service" if service else "New Service")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "ServiceDialog")

        self._build_ui()
        if service:
            self._prefill_from_service(service)

    def closeEvent(self, event):
        save_geometry(self, "ServiceDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the Name, Description, Price, and Active fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name, e.g. 'Screen Replacement' (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Description (optional)")
        self.description_input.setFixedHeight(80)

        self.price_input = QDoubleSpinBox()
        self.price_input.setPrefix("$")
        self.price_input.setDecimals(2)
        self.price_input.setMinimum(0.01)
        self.price_input.setMaximum(99999.99)
        self.price_input.setValue(50.00)

        self.active_checkbox = QCheckBox("Active (shows up as an option for new bills)")
        self.active_checkbox.setChecked(True)

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

        for label_text, widget in [
            ("Name", self.name_input),
            ("Description", self.description_input),
            ("Price", self.price_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.active_checkbox)
        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)
        self.name_input.setFocus()

    def _prefill_from_service(self, service: dict):
        self.name_input.setText(service.get("name", ""))
        self.description_input.setPlainText(service.get("description") or "")
        self.price_input.setValue(float(service.get("price", 0)))
        self.active_checkbox.setChecked(service.get("is_active", True))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Enter a name.")
            return

        payload = {
            "name": name,
            "description": self.description_input.toPlainText().strip() or None,
            "price": f"{self.price_input.value():.2f}",
            "is_active": self.active_checkbox.isChecked(),
        }

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        service_id = self.service["id"] if self.service else None
        self._thread = QThread()
        self._worker = LookupSaveWorker(ENDPOINT, payload, service_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            result: The saved record on success, or the caught
                ApiError on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save")

        if not success:
            self.handle_api_error(result, on_other_error=self._show_error)
            return

        self.saved_service = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
