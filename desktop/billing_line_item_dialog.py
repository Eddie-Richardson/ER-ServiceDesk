# ER-ServiceDesk/desktop/billing_line_item_dialog.py

"""
Dialog for adding a new line item to a quote or invoice, or editing an
existing one's quantity -- shared by both QuoteDetailDialog and
InvoiceDetailDialog, parameterized by which add/update/remove
functions to call rather than two near-identical dialog classes.

A line item is either a Service or a real inventory Part -- a type
toggle switches which picker is shown. Only Parts with a selling_price
configured are offered, since one without would just be rejected
server-side; better to never show it as an option at all.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
)

from desktop import layout
from desktop.api_client import ApiError


class BillingLineItemDialog(QDialog):
    """
    Modal dialog for adding or editing a line item on a quote or invoice.

    Pass `line_item=None` to add a new one, or an existing line item
    dict to edit its quantity. On a successful save, the dialog closes
    itself and the saved record is available via `self.saved_line_item`.
    """

    def __init__(
        self,
        parent_id: int,
        services: list[dict],
        add_func,
        update_func,
        remove_func,
        line_item: dict | None = None,
        parent=None,
        parts: list[dict] | None = None,
    ):
        """
        Args:
            parent_id: The quote or invoice id this line item belongs to.
            services: Every active service, for the picker.
            add_func: Called as add_func(parent_id, quantity,
                service_id=..., part_id=...) to create a new line item
                -- exactly one of service_id/part_id is passed.
            update_func: Called as update_func(line_item_id, quantity)
                to update an existing one.
            remove_func: Called as remove_func(line_item_id) to remove
                an existing one.
            parts: Every part with a selling_price configured, for the
                picker. Empty/None means the Part option is hidden --
                nothing to pick from.
        """
        super().__init__(parent)
        self.parent_id = parent_id
        self.services = services
        self.parts = parts or []
        self.add_func = add_func
        self.update_func = update_func
        self.remove_func = remove_func
        self.line_item = line_item
        self.saved_line_item: dict | None = None
        self.deleted = False

        self.setWindowTitle("Edit Line Item" if line_item else "Add Line Item")
        self.setMinimumWidth(layout.DIALOG_WIDTH)

        self._build_ui()
        if line_item:
            self._prefill_from_line_item(line_item)

    def _build_ui(self):
        """Builds the type toggle, Service/Part pickers, and Quantity field."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.service_type_radio = QRadioButton("Service")
        self.part_type_radio = QRadioButton("Part")
        self.service_type_radio.setChecked(True)
        self.service_type_radio.toggled.connect(self._on_type_toggled)

        outer_layout.addWidget(self.service_type_radio)
        outer_layout.addWidget(self.part_type_radio)

        self.service_combo = QComboBox()
        for service in self.services:
            price_label = f"{service['name']} (${service['price']})"
            self.service_combo.addItem(price_label, userData=service["id"])

        self.part_combo = QComboBox()
        for part in self.parts:
            price_label = f"{part['name']} (${part['selling_price']}) -- {part['quantity_on_hand']} on hand"
            self.part_combo.addItem(price_label, userData=part["id"])

        if not self.parts:
            self.part_type_radio.setEnabled(False)
            self.part_type_radio.setToolTip("No parts have a selling price configured yet -- set one in Inventory first.")

        if self.line_item:
            self.service_type_radio.setEnabled(False)
            self.part_type_radio.setEnabled(False)
            self.service_combo.setEnabled(False)
            self.part_combo.setEnabled(False)

        self.quantity_input = QSpinBox()
        self.quantity_input.setMinimum(1)
        self.quantity_input.setMaximum(999)
        self.quantity_input.setValue(1)

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

        self.delete_button = None
        if self.line_item:
            self.delete_button = QPushButton("Remove Line Item")
            self.delete_button.setObjectName("danger")
            self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
            self.delete_button.clicked.connect(self._attempt_delete)

        outer_layout.addWidget(self.service_combo)
        outer_layout.addWidget(self.part_combo)

        quantity_label = QLabel("Quantity")
        quantity_label.setObjectName("subtitle")
        outer_layout.addWidget(quantity_label)
        outer_layout.addWidget(self.quantity_input)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        if self.delete_button:
            outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)
        self._on_type_toggled()

    def _on_type_toggled(self):
        """Shows only the picker matching the currently-selected type."""
        self.service_combo.setVisible(self.service_type_radio.isChecked())
        self.part_combo.setVisible(self.part_type_radio.isChecked())

    def _prefill_from_line_item(self, line_item: dict):
        if line_item.get("part_id") is not None:
            self.part_type_radio.setChecked(True)
            index = self.part_combo.findData(line_item.get("part_id"))
            if index >= 0:
                self.part_combo.setCurrentIndex(index)
        else:
            self.service_type_radio.setChecked(True)
            index = self.service_combo.findData(line_item.get("service_id"))
            if index >= 0:
                self.service_combo.setCurrentIndex(index)
        self._on_type_toggled()
        self.quantity_input.setValue(line_item.get("quantity", 1))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then saves synchronously -- a small, infrequent action, not worth the complexity of a background thread."""
        is_part = self.part_type_radio.isChecked()
        selected_id = self.part_combo.currentData() if is_part else self.service_combo.currentData()
        if selected_id is None:
            self._show_error(f"Select a {'part' if is_part else 'service'}.")
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        try:
            if self.line_item:
                result = self.update_func(self.line_item["id"], self.quantity_input.value())
            elif is_part:
                result = self.add_func(self.parent_id, self.quantity_input.value(), part_id=selected_id)
            else:
                result = self.add_func(self.parent_id, self.quantity_input.value(), service_id=selected_id)
        except ApiError as e:
            self.save_button.setEnabled(True)
            self.save_button.setText("Save")
            self._show_error(str(e))
            return

        self.save_button.setEnabled(True)
        self.save_button.setText("Save")
        self.saved_line_item = result
        self.accept()

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete(self):
        """Confirms, then removes this line item."""
        confirmed = QMessageBox.question(
            self,
            "Remove Line Item",
            "Remove this line item? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)
        try:
            self.remove_func(self.line_item["id"])
        except ApiError as e:
            self._show_error(str(e))
            return
        finally:
            self.delete_button.setEnabled(True)

        self.deleted = True
        self.accept()
