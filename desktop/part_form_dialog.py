# ER-ServiceDesk/desktop/part_form_dialog.py

"""
Dialog for creating a new part or editing an existing one.

Location is the only foreign key here, populated as a dropdown from the
backend. Supplier stays free text -- supplier names are genuinely
open-ended and shop-specific, not a small closed set worth a lookup
table. Quantity and reorder threshold are plain integer fields; a part
at or below its reorder threshold is what drives the Low Stock view in
the Inventory window's Parts tab.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from desktop import layout
from desktop.part_save_worker import PartSaveWorker


class PartFormDialog(QDialog):
    """
    Modal dialog for creating or editing a part.

    Pass `part=None` to create a new part, or an existing part dict (as
    returned by GET /inventory/parts/{id}) to edit one. On a successful
    save, the dialog closes itself and the saved part record is
    available via `self.saved_part`.
    """

    def __init__(self, reference_data: dict, part: dict | None = None, parent=None):
        """
        Args:
            reference_data: Dict with key "locations" -- the lookup list
                loaded by InventoryDataWorker.
            part: An existing part dict to edit, or None to create a
                new one.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.reference_data = reference_data
        self.part = part
        self.saved_part: dict | None = None

        self._thread: QThread | None = None
        self._worker: PartSaveWorker | None = None

        self.setWindowTitle("Edit Part" if part else "New Part")
        self.setFixedWidth(layout.DIALOG_WIDTH + 40)

        self._build_ui()
        if part:
            self._prefill_from_part(part)

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

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Part name (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.sku_input = QLineEdit()
        self.sku_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.quantity_input = QSpinBox()
        self.quantity_input.setRange(0, 1_000_000)
        self.quantity_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.reorder_threshold_input = QSpinBox()
        self.reorder_threshold_input.setRange(0, 1_000_000)
        self.reorder_threshold_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.unit_cost_input = QLineEdit()
        self.unit_cost_input.setPlaceholderText("e.g. 12.99 (optional)")
        self.unit_cost_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.supplier_input = QLineEdit()
        self.supplier_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.location_combo = QComboBox()
        self.location_combo.setFixedHeight(layout.INPUT_HEIGHT)
        self.location_combo.addItem("-- None --", userData=None)
        for location in self.reference_data.get("locations", []):
            self.location_combo.addItem(location["name"], userData=location["id"])

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes (optional)")
        self.notes_input.setFixedHeight(80)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Part")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("Name", self.name_input),
            ("SKU", self.sku_input),
            ("Quantity On Hand", self.quantity_input),
            ("Reorder Threshold", self.reorder_threshold_input),
            ("Unit Cost", self.unit_cost_input),
            ("Supplier", self.supplier_input),
            ("Location", self.location_combo),
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

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_part(self, part: dict):
        """
        Populates every field from an existing part record, for edit mode.

        Args:
            part: The part dict being edited.
        """
        self.name_input.setText(part.get("name", ""))
        self.sku_input.setText(part.get("sku") or "")
        self.quantity_input.setValue(part.get("quantity_on_hand", 0))
        self.reorder_threshold_input.setValue(part.get("reorder_threshold", 0))
        self.unit_cost_input.setText(
            "" if part.get("unit_cost") is None else str(part["unit_cost"])
        )
        self.supplier_input.setText(part.get("supplier") or "")

        index = self.location_combo.findData(part.get("location_id"))
        if index >= 0:
            self.location_combo.setCurrentIndex(index)

        self.notes_input.setPlainText(part.get("notes") or "")

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

        part_id = self.part["id"] if self.part else None
        self._thread = QThread()
        self._worker = PartSaveWorker(payload, part_id)
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
        name = self.name_input.text().strip()
        if not name:
            return {}, "Enter a name."

        unit_cost_text = self.unit_cost_input.text().strip()
        unit_cost = None
        if unit_cost_text:
            try:
                unit_cost = float(unit_cost_text)
            except ValueError:
                return {}, "Unit cost must be a number, e.g. 12.99."

        payload = {
            "name": name,
            "sku": self.sku_input.text().strip() or None,
            "quantity_on_hand": self.quantity_input.value(),
            "reorder_threshold": self.reorder_threshold_input.value(),
            "unit_cost": unit_cost,
            "supplier": self.supplier_input.text().strip() or None,
            "location_id": self.location_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip() or None,
        }
        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Handles the save worker's result. Closes the dialog on success,
        or re-enables the form and shows the error inline on failure.

        Args:
            success: Whether the save succeeded.
            result: The saved part record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Part")

        if not success:
            self._show_error(result)
            return

        self.saved_part = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
