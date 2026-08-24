# ER-ServiceDesk/desktop/name_percentage_dialog.py

"""
Generic dialog for creating or editing a name + percentage + active
catalog item -- shared by Discounts and Tax Rates (both structurally
identical: a name, a percentage, and a toggle for whether it currently
shows up as an option for new bills), parameterized by display name
and endpoint rather than two near-identical dialog classes.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from desktop import layout
from desktop.base_dialog import AppDialog
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.lookup_save_worker import LookupSaveWorker


class NamePercentageDialog(AppDialog):
    """
    Modal dialog for creating or editing a name/percentage/is_active
    catalog item.

    Pass `item=None` to create a new item, or an existing item dict to
    edit one. On a successful save, the dialog closes itself and the
    saved record is available via `self.saved_item`.
    """

    def __init__(self, display_name: str, endpoint: str, item: dict | None = None, parent=None):
        """
        Args:
            display_name: Shown in the dialog title, e.g. "Discount".
            endpoint: The resource path, e.g. "/discounts/".
        """
        super().__init__(parent)
        self.endpoint = endpoint
        self.item = item
        self.saved_item: dict | None = None

        self._thread: QThread | None = None
        self._worker: LookupSaveWorker | None = None

        self.setWindowTitle(f"Edit {display_name}" if item else f"New {display_name}")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "NamePercentageDialog")

        self._build_ui()
        if item:
            self._prefill_from_item(item)

    def closeEvent(self, event):
        save_geometry(self, "NamePercentageDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the Name, Percentage, and Active fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name, e.g. 'Teacher' (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.percentage_input = QDoubleSpinBox()
        self.percentage_input.setSuffix("%")
        self.percentage_input.setDecimals(2)
        self.percentage_input.setMinimum(0.01)
        self.percentage_input.setMaximum(100.00)
        self.percentage_input.setValue(10.00)

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
            ("Percentage", self.percentage_input),
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

    def _prefill_from_item(self, item: dict):
        self.name_input.setText(item.get("name", ""))
        self.percentage_input.setValue(float(item.get("percentage", 0)))
        self.active_checkbox.setChecked(item.get("is_active", True))

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
            "percentage": f"{self.percentage_input.value():.2f}",
            "is_active": self.active_checkbox.isChecked(),
        }

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        item_id = self.item["id"] if self.item else None
        self._thread = QThread()
        self._worker = LookupSaveWorker(self.endpoint, payload, item_id)
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

        self.saved_item = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
