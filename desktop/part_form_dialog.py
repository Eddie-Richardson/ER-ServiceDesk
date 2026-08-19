# ER-ServiceDesk/desktop/part_form_dialog.py

"""
Dialog for creating a new part or editing an existing one.

A part can be split across several locations at once (some on the
shelf, some at a bench), so its stock isn't one Location dropdown and
one Quantity field -- it's a small editable list, one row per location,
each with its own quantity. Rows can be added or removed freely; the
running total (shown live) is what actually gets compared against the
part's reorder threshold, not any single row.

Supplier stays free text -- supplier names are genuinely open-ended and
shop-specific, not a small closed set worth a lookup table.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.base_dialog import AppDialog
from desktop.part_save_worker import PartSaveWorker


class PartFormDialog(AppDialog):
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
        """
        super().__init__(parent)
        self.reference_data = reference_data
        self.part = part
        self.saved_part: dict | None = None
        self.location_rows: list[dict] = []  # each: {"widget", "combo", "spinbox"}

        self._thread: QThread | None = None
        self._worker: PartSaveWorker | None = None

        self.setWindowTitle("Edit Part" if part else "New Part")
        self.setFixedWidth(layout.DIALOG_WIDTH + 100)

        self._build_ui()
        if part:
            self._prefill_from_part(part)
        else:
            self._add_location_row()  # start with one empty row rather than a blank list

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds every field, including the multi-row location editor."""
        content = QWidget()
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

        self.reorder_threshold_input = QSpinBox()
        self.reorder_threshold_input.setRange(0, 1_000_000)
        self.reorder_threshold_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.unit_cost_input = QLineEdit()
        self.unit_cost_input.setPlaceholderText("e.g. 12.99 (optional)")
        self.unit_cost_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.selling_price_input = QLineEdit()
        self.selling_price_input.setPlaceholderText("e.g. 24.99 -- what a customer is billed when this part is used on an invoice (optional, but required before it can actually be billed)")
        self.selling_price_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.supplier_input = QLineEdit()
        self.supplier_input.setFixedHeight(layout.INPUT_HEIGHT)

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
            ("Reorder Threshold (total across all locations)", self.reorder_threshold_input),
            ("Unit Cost", self.unit_cost_input),
            ("Selling Price", self.selling_price_input),
            ("Supplier", self.supplier_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self._build_locations_section())

        notes_label = QLabel("Notes")
        notes_label.setObjectName("subtitle")
        outer_layout.addWidget(notes_label)
        outer_layout.addWidget(self.notes_input)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        content.setLayout(outer_layout)
        self.set_scrollable_content(content)

    def _build_locations_section(self) -> QWidget:
        """
        Builds the "Stock by Location" section: a live total, an area
        that holds one row per location, and an Add Location button.

        Returns:
            The assembled section as a single QWidget.
        """
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(layout.SPACE_XS)

        section_label = QLabel("Stock by Location")
        section_label.setObjectName("subtitle")
        section_layout.addWidget(section_label)

        self.total_label = QLabel("Total: 0")
        section_layout.addWidget(self.total_label)

        self.locations_container = QWidget()
        self.locations_container_layout = QVBoxLayout()
        self.locations_container_layout.setContentsMargins(0, 0, 0, 0)
        self.locations_container_layout.setSpacing(layout.SPACE_XS)
        self.locations_container.setLayout(self.locations_container_layout)
        section_layout.addWidget(self.locations_container)

        add_location_button = QPushButton("+ Add Location")
        add_location_button.setObjectName("secondary")
        add_location_button.clicked.connect(lambda: self._add_location_row())
        section_layout.addWidget(add_location_button)

        section.setLayout(section_layout)
        return section

    def _add_location_row(self, location_id=None, quantity: int = 0):
        """
        Appends one Location + Quantity + Remove row to the locations
        editor.

        Args:
            location_id: The location to pre-select, or None to leave
                the "-- Select Location --" placeholder selected.
            quantity: The quantity to pre-fill for this row.
        """
        row_widget = QWidget()
        row_layout = QHBoxLayout()
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.setSpacing(layout.SPACE_SM)

        location_combo = QComboBox()
        location_combo.setFixedHeight(layout.INPUT_HEIGHT)
        location_combo.addItem("-- Select Location --", userData=None)
        for loc in self.reference_data.get("locations", []):
            location_combo.addItem(loc["name"], userData=loc["id"])
        index = location_combo.findData(location_id)
        if index >= 0:
            location_combo.setCurrentIndex(index)

        quantity_input = QSpinBox()
        quantity_input.setRange(0, 1_000_000)
        quantity_input.setValue(quantity)
        quantity_input.setFixedHeight(layout.INPUT_HEIGHT)
        quantity_input.valueChanged.connect(self._update_total_label)

        remove_button = QPushButton("Remove")
        remove_button.setObjectName("secondary")
        remove_button.setFixedHeight(layout.INPUT_HEIGHT)

        row_layout.addWidget(location_combo, stretch=2)
        row_layout.addWidget(quantity_input, stretch=1)
        row_layout.addWidget(remove_button)
        row_widget.setLayout(row_layout)

        row_entry = {"widget": row_widget, "combo": location_combo, "spinbox": quantity_input}
        remove_button.clicked.connect(lambda: self._remove_location_row(row_entry))

        self.locations_container_layout.addWidget(row_widget)
        self.location_rows.append(row_entry)
        self._update_total_label()

    def _remove_location_row(self, row_entry: dict):
        self.location_rows.remove(row_entry)
        row_entry["widget"].deleteLater()
        self._update_total_label()

    def _update_total_label(self):
        """Recomputes and displays the sum of every row's quantity."""
        total = sum(row["spinbox"].value() for row in self.location_rows)
        self.total_label.setText(f"Total: {total}")

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_part(self, part: dict):
        """
        Populates every field from an existing part record, including
        one location row per entry in its current breakdown. If the
        part has no stock recorded anywhere yet, starts with one empty
        row rather than leaving the section blank.
        """
        self.name_input.setText(part.get("name", ""))
        self.sku_input.setText(part.get("sku") or "")
        self.reorder_threshold_input.setValue(part.get("reorder_threshold", 0))
        self.unit_cost_input.setText(
            "" if part.get("unit_cost") is None else str(part["unit_cost"])
        )
        self.selling_price_input.setText(
            "" if part.get("selling_price") is None else str(part["selling_price"])
        )
        self.supplier_input.setText(part.get("supplier") or "")
        self.notes_input.setPlainText(part.get("notes") or "")

        existing_locations = part.get("locations") or []
        if existing_locations:
            for entry in existing_locations:
                self._add_location_row(entry["location_id"], entry["quantity"])
        else:
            self._add_location_row()

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
        Validates every required field, including the location rows
        (each filled-in row needs a location selected, and no location
        can appear twice), then assembles the request payload.

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

        selling_price_text = self.selling_price_input.text().strip()
        selling_price = None
        if selling_price_text:
            try:
                selling_price = float(selling_price_text)
            except ValueError:
                return {}, "Selling price must be a number, e.g. 24.99."

        locations = []
        seen_location_ids = set()
        for row in self.location_rows:
            location_id = row["combo"].currentData()
            if location_id is None:
                continue  # an unfilled placeholder row -- not an error, just skipped
            if location_id in seen_location_ids:
                location_name = row["combo"].currentText()
                return {}, f"'{location_name}' is used in more than one row. Each location can only appear once."
            seen_location_ids.add(location_id)
            locations.append({"location_id": location_id, "quantity": row["spinbox"].value()})

        payload = {
            "name": name,
            "sku": self.sku_input.text().strip() or None,
            "reorder_threshold": self.reorder_threshold_input.value(),
            "unit_cost": unit_cost,
            "selling_price": selling_price,
            "supplier": self.supplier_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
            "locations": locations,
        }
        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Handles the save worker's result. Closes the dialog on success,
        or re-enables the form and shows the error inline on failure.

        Args:
            result: The saved part record on success, or the caught
                ApiError on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Part")

        if not success:
            self.handle_api_error(result, on_other_error=self._show_error)
            return

        self.saved_part = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()
