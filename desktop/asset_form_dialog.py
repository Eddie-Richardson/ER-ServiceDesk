# ER-ServiceDesk/desktop/asset_form_dialog.py

"""
Dialog for creating a new asset or editing an existing one.

Status and Condition are fixed short lists (mirroring how Ticket
Priority is handled) rather than backend lookup tables -- their real-
world vocabularies are small and stable ("Active"/"In Repair"/"Retired",
"New"/"Good"/"Fair"/"Damaged"). Category and Location are proper foreign
keys, populated as dropdowns from the backend so they can't drift out of
sync the way free text would. Everything else (name, sku, manufacturer,
model, serial number, assigned_to, notes) is genuinely open-ended free
text; price/dates are free text too, parsed and validated on save rather
than forced into date-picker widgets that don't have a clean "not set"
state for an optional field.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.asset_save_worker import AssetSaveWorker
from desktop.window_geometry import restore_geometry, save_geometry

STATUS_OPTIONS = ["Active", "In Repair", "Retired"]
CONDITION_OPTIONS = ["New", "Good", "Fair", "Damaged"]


class AssetFormDialog(QDialog):
    """
    Modal dialog for creating or editing an asset.

    Pass `asset=None` to create a new asset, or an existing asset dict
    (as returned by GET /inventory/assets/{id}) to edit one. On a
    successful save, the dialog closes itself and the saved asset record
    is available via `self.saved_asset`.
    """

    def __init__(self, reference_data: dict, asset: dict | None = None, parent=None):
        """
        Args:
            reference_data: Dict with keys "categories", "locations" --
                the lookup lists loaded by InventoryDataWorker.
        """
        super().__init__(parent)
        self.reference_data = reference_data
        self.asset = asset
        self.saved_asset: dict | None = None

        self._thread: QThread | None = None
        self._worker: AssetSaveWorker | None = None

        self.setWindowTitle("Edit Asset" if asset else "New Asset")
        self.setMinimumWidth(layout.DIALOG_WIDTH + 80)
        self.resize(layout.DIALOG_WIDTH + 80, 560)
        restore_geometry(self, "AssetFormDialog")

        self._build_ui()
        if asset:
            self._prefill_from_asset(asset)

    def closeEvent(self, event):
        save_geometry(self, "AssetFormDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """
        Builds every field inside a scroll area, so the dialog can be
        resized shorter than its full content without cutting anything
        off. Save/Cancel and the error message stay pinned outside the
        scroll area at the bottom -- always reachable regardless of
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

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Asset name (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.sku_input = QLineEdit()
        self.sku_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.category_combo = self._make_optional_combo()
        for category in self.reference_data.get("categories", []):
            self.category_combo.addItem(category["name"], userData=category["id"])

        self.manufacturer_input = QLineEdit()
        self.manufacturer_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.model_input = QLineEdit()
        self.model_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.serial_number_input = QLineEdit()
        self.serial_number_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.status_combo = self._make_optional_combo()
        for status_name in STATUS_OPTIONS:
            self.status_combo.addItem(status_name, userData=status_name)

        self.location_combo = self._make_optional_combo()
        for location in self.reference_data.get("locations", []):
            self.location_combo.addItem(location["name"], userData=location["id"])

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("e.g. 499.99")
        self.price_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.purchase_date_input = QLineEdit()
        self.purchase_date_input.setPlaceholderText("YYYY-MM-DD")
        self.purchase_date_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.warranty_expiration_input = QLineEdit()
        self.warranty_expiration_input.setPlaceholderText("YYYY-MM-DD")
        self.warranty_expiration_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.assigned_to_input = QLineEdit()
        self.assigned_to_input.setPlaceholderText("Person or department (optional)")
        self.assigned_to_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.condition_combo = self._make_optional_combo()
        for condition_name in CONDITION_OPTIONS:
            self.condition_combo.addItem(condition_name, userData=condition_name)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes (optional)")
        self.notes_input.setFixedHeight(80)

        for label_text, widget in [
            ("Name", self.name_input),
            ("SKU", self.sku_input),
            ("Category", self.category_combo),
            ("Manufacturer", self.manufacturer_input),
            ("Model", self.model_input),
            ("Serial Number", self.serial_number_input),
            ("Status", self.status_combo),
            ("Location", self.location_combo),
            ("Price", self.price_input),
            ("Purchase Date", self.purchase_date_input),
            ("Warranty Expiration", self.warranty_expiration_input),
            ("Assigned To", self.assigned_to_input),
            ("Condition", self.condition_combo),
            ("Notes", self.notes_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            content_layout.addWidget(field_label)
            content_layout.addWidget(widget)

        content_widget.setLayout(content_layout)
        scroll_area.setWidget(content_widget)
        outer_layout.addWidget(scroll_area)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Asset")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        bottom_bar = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.SPACE_SM,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        bottom_layout.setSpacing(layout.SPACE_SM)
        bottom_layout.addWidget(self.error_label)
        bottom_layout.addWidget(self.save_button)
        bottom_layout.addWidget(cancel_button)
        bottom_bar.setLayout(bottom_layout)
        outer_layout.addWidget(bottom_bar)

        self.setLayout(outer_layout)

    def _make_optional_combo(self) -> QComboBox:
        """
        Builds a QComboBox pre-seeded with a blank "-- None --" entry, for
        fields that are optional foreign keys or fixed-list values.

        Returns:
            A QComboBox with userData=None as its first item.
        """
        combo = QComboBox()
        combo.setFixedHeight(layout.INPUT_HEIGHT)
        combo.addItem("-- None --", userData=None)
        return combo

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_asset(self, asset: dict):
        self.name_input.setText(asset.get("name", ""))
        self.sku_input.setText(asset.get("sku") or "")
        self._select_combo_by_data(self.category_combo, asset.get("category_id"))
        self.manufacturer_input.setText(asset.get("manufacturer") or "")
        self.model_input.setText(asset.get("model") or "")
        self.serial_number_input.setText(asset.get("serial_number") or "")
        self._select_combo_by_data(self.status_combo, asset.get("status"))
        self._select_combo_by_data(self.location_combo, asset.get("location_id"))
        self.price_input.setText(
            "" if asset.get("price") is None else str(asset["price"])
        )
        self.purchase_date_input.setText(asset.get("purchase_date") or "")
        self.warranty_expiration_input.setText(asset.get("warranty_expiration") or "")
        self.assigned_to_input.setText(asset.get("assigned_to") or "")
        self._select_combo_by_data(self.condition_combo, asset.get("condition"))
        self.notes_input.setPlainText(asset.get("notes") or "")

    def _select_combo_by_data(self, combo: QComboBox, data_value):
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

        asset_id = self.asset["id"] if self.asset else None
        self._thread = QThread()
        self._worker = AssetSaveWorker(payload, asset_id)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _build_payload(self) -> tuple[dict, str]:
        """
        Validates the required field and any optional fields with a
        specific format (price, dates), then assembles the request
        payload.

        Returns:
            A (payload, error_message) tuple. error_message is empty if
            validation passed.
        """
        name = self.name_input.text().strip()
        if not name:
            return {}, "Enter a name."

        price_text = self.price_input.text().strip()
        price = None
        if price_text:
            try:
                price = float(price_text)
            except ValueError:
                return {}, "Price must be a number, e.g. 499.99."

        purchase_date = self.purchase_date_input.text().strip() or None
        warranty_expiration = self.warranty_expiration_input.text().strip() or None
        for label, value in [("Purchase date", purchase_date), ("Warranty expiration", warranty_expiration)]:
            if value and not self._looks_like_date(value):
                return {}, f"{label} must be in YYYY-MM-DD format."

        payload = {
            "name": name,
            "sku": self.sku_input.text().strip() or None,
            "category_id": self.category_combo.currentData(),
            "manufacturer": self.manufacturer_input.text().strip() or None,
            "model": self.model_input.text().strip() or None,
            "serial_number": self.serial_number_input.text().strip() or None,
            "status": self.status_combo.currentData(),
            "location_id": self.location_combo.currentData(),
            "price": price,
            "purchase_date": purchase_date,
            "warranty_expiration": warranty_expiration,
            "assigned_to": self.assigned_to_input.text().strip() or None,
            "condition": self.condition_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip() or None,
        }
        return payload, ""

    def _looks_like_date(self, value: str) -> bool:
        """
        Returns:
            Whether value matches YYYY-MM-DD shape. Deliberately simple
            (length + dash positions) rather than a full parse -- this is
            a friendly format hint, not a calendar validity check; the
            backend still validates the real date on save.
        """
        return len(value) == 10 and value[4] == "-" and value[7] == "-"

    def _on_save_finished(self, success: bool, result):
        """
        Handles the save worker's result. Closes the dialog on success,
        or re-enables the form and shows the error inline on failure.

        Args:
            result: The saved asset record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Asset")

        if not success:
            self._show_error(result)
            return

        self.saved_asset = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()