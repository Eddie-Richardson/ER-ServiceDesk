# ER-ServiceDesk/desktop/billing_line_item_dialog.py

"""
Dialog for adding a new line item to a quote or invoice, or editing an
existing one's quantity -- shared by both QuoteDetailDialog and
InvoiceDetailDialog, parameterized by which add/update/remove
functions to call rather than two near-identical dialog classes.
"""

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QLabel,
    QMessageBox,
    QPushButton,
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
    ):
        """
        Args:
            parent_id: The quote or invoice id this line item belongs to.
            services: Every active service, for the picker.
            add_func: Called as add_func(parent_id, service_id, quantity)
                to create a new line item.
            update_func: Called as update_func(line_item_id, quantity)
                to update an existing one.
            remove_func: Called as remove_func(line_item_id) to remove
                an existing one.
            line_item: An existing line item dict to edit, or None to
                add a new one.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.parent_id = parent_id
        self.services = services
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
        """Builds the Service picker and Quantity fields."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.service_combo = QComboBox()
        for service in self.services:
            price_label = f"{service['name']} (${service['price']})"
            self.service_combo.addItem(price_label, userData=service["id"])
        if self.line_item:
            self.service_combo.setEnabled(False)

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

        for label_text, widget in [
            ("Service", self.service_combo),
            ("Quantity", self.quantity_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)
        if self.delete_button:
            outer_layout.addWidget(self.delete_button)

        self.setLayout(outer_layout)

    def _prefill_from_line_item(self, line_item: dict):
        """
        Args:
            line_item: The line item dict being edited.
        """
        index = self.service_combo.findData(line_item.get("service_id"))
        if index >= 0:
            self.service_combo.setCurrentIndex(index)
        self.quantity_input.setValue(line_item.get("quantity", 1))

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then saves synchronously -- a small, infrequent action, matching the same no-QThread reasoning used elsewhere tonight."""
        service_id = self.service_combo.currentData()
        if service_id is None:
            self._show_error("Select a service.")
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        try:
            if self.line_item:
                result = self.update_func(self.line_item["id"], self.quantity_input.value())
            else:
                result = self.add_func(self.parent_id, service_id, self.quantity_input.value())
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
        """
        Args:
            message: The error text to show below the form.
        """
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
