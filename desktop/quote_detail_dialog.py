# ER-ServiceDesk/desktop/quote_detail_dialog.py

"""
Dialog for viewing and managing a single quote -- its line items,
discount/tax selection, computed totals, and converting it into a
real invoice once approved.

Only line items get their own expandable add/edit/remove flow (the
same pattern as TicketPart); discount/tax selection updates the quote
immediately when changed, matching the same "toggle applies right
away, no separate Save step" pattern used for the Ticket Type Stage
pairing screen.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.billing_line_item_dialog import BillingLineItemDialog
from desktop.window_geometry import restore_geometry, save_geometry

LINE_ITEM_COLUMN_HEADERS = ["Service", "Qty", "Unit Price", "Line Total"]


class QuoteDetailDialog(QDialog):
    """Modal dialog for viewing and managing a single quote."""

    def __init__(self, quote_id: int, ticket_title: str, parent=None):
        """
        Args:
            quote_id: The quote to display.
            ticket_title: Shown in the window title for context.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.quote_id = quote_id
        self.quote: dict | None = None
        self.services: list[dict] = []
        self.converted = False  # tracked so the caller (BillingDialog) knows to refresh its invoice list too

        self.setWindowTitle(f"Quote - {ticket_title}")
        self.resize(560, 520)
        restore_geometry(self, "QuoteDetailDialog")

        self._build_ui()
        self._load_services()
        self._load_quote()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "QuoteDetailDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the line items table, discount/tax pickers, totals summary, and convert button."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        items_label = QLabel("Line Items")
        items_label.setObjectName("subtitle")
        outer_layout.addWidget(items_label)

        add_item_button = QPushButton("Add Line Item")
        add_item_button.setObjectName("secondary")
        add_item_button.clicked.connect(self._on_add_line_item)
        outer_layout.addWidget(add_item_button)

        self.line_items_table = QTableWidget()
        self.line_items_table.setColumnCount(len(LINE_ITEM_COLUMN_HEADERS))
        self.line_items_table.setHorizontalHeaderLabels(LINE_ITEM_COLUMN_HEADERS)
        self.line_items_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.line_items_table.verticalHeader().setVisible(False)
        self.line_items_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.line_items_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.line_items_table.doubleClicked.connect(self._on_line_item_double_clicked)
        outer_layout.addWidget(self.line_items_table)

        picker_row = QHBoxLayout()
        picker_row.addWidget(QLabel("Discount:"))
        self.discount_combo = QComboBox()
        self.discount_combo.currentIndexChanged.connect(self._on_discount_changed)
        picker_row.addWidget(self.discount_combo)
        picker_row.addWidget(QLabel("Tax:"))
        self.tax_combo = QComboBox()
        self.tax_combo.currentIndexChanged.connect(self._on_tax_changed)
        picker_row.addWidget(self.tax_combo)
        outer_layout.addLayout(picker_row)

        self.totals_label = QLabel("")
        self.totals_label.setObjectName("subtitle")
        outer_layout.addWidget(self.totals_label)

        self.convert_button = QPushButton("Convert to Invoice")
        self.convert_button.clicked.connect(self._on_convert_to_invoice)
        outer_layout.addWidget(self.convert_button)

        self.converted_label = QLabel("")
        self.converted_label.setObjectName("subtitle")
        self.converted_label.hide()
        outer_layout.addWidget(self.converted_label)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------
    def _load_services(self):
        """Loads every active service for the line-item picker."""
        try:
            all_services = api_client.list_services()
        except ApiError:
            all_services = []
        self.services = [s for s in all_services if s.get("is_active", True)]

    def _load_quote(self):
        """Fetches the quote, populates the discount/tax pickers, and renders the line items and totals."""
        try:
            self.quote = api_client.get_quote(self.quote_id)
        except ApiError as e:
            QMessageBox.critical(self, "Load Failed", str(e))
            return

        self._populate_discount_tax_pickers()
        self._render_line_items()
        self._render_totals()
        self._update_convert_visibility()

    def _populate_discount_tax_pickers(self):
        """Fills the Discount/Tax dropdowns with active options, plus the currently-selected one even if it's since been deactivated."""
        try:
            discounts = api_client.list_discounts()
        except ApiError:
            discounts = []
        try:
            tax_rates = api_client.list_tax_rates()
        except ApiError:
            tax_rates = []

        self.discount_combo.blockSignals(True)
        self.discount_combo.clear()
        self.discount_combo.addItem("None", userData=None)
        current_discount_id = self.quote.get("discount_id")
        for d in discounts:
            if d.get("is_active", True) or d["id"] == current_discount_id:
                self.discount_combo.addItem(f"{d['name']} ({d['percentage']}%)", userData=d["id"])
        idx = self.discount_combo.findData(current_discount_id)
        self.discount_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.discount_combo.blockSignals(False)

        self.tax_combo.blockSignals(True)
        self.tax_combo.clear()
        self.tax_combo.addItem("None", userData=None)
        current_tax_id = self.quote.get("tax_rate_id")
        for t in tax_rates:
            if t.get("is_active", True) or t["id"] == current_tax_id:
                self.tax_combo.addItem(f"{t['name']} ({t['percentage']}%)", userData=t["id"])
        idx = self.tax_combo.findData(current_tax_id)
        self.tax_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.tax_combo.blockSignals(False)

    def _render_line_items(self):
        """Renders the quote's current line items into the table."""
        line_items = self.quote.get("line_items", [])
        self.line_items_table.setRowCount(len(line_items))
        for row, item in enumerate(line_items):
            line_total = float(item["unit_price"]) * item["quantity"]
            values = [
                item["service_name"],
                str(item["quantity"]),
                f"${item['unit_price']}",
                f"${line_total:.2f}",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item)
                self.line_items_table.setItem(row, col, cell)

    def _render_totals(self):
        """Renders the Subtotal/Discount/Tax/Total summary."""
        self.totals_label.setText(
            f"Subtotal: ${self.quote['subtotal']}   "
            f"Discount: -${self.quote['discount_amount']}   "
            f"Tax: +${self.quote['tax_amount']}   "
            f"Total: ${self.quote['total']}"
        )

    def _update_convert_visibility(self):
        """Shows the Convert button only if this quote hasn't already been converted."""
        already_converted = self.quote.get("converted_invoice_id") is not None
        self.convert_button.setVisible(not already_converted)
        if already_converted:
            self.converted_label.setText(f"Converted to Invoice #{self.quote['converted_invoice_id']}.")
            self.converted_label.show()
        else:
            self.converted_label.hide()

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def _on_add_line_item(self):
        """Opens BillingLineItemDialog in add mode; reloads the quote if a line item was added."""
        if not self.services:
            QMessageBox.information(self, "No Services", "No active services are configured yet -- add one in Settings first.")
            return

        dialog = BillingLineItemDialog(
            self.quote_id, self.services,
            api_client.add_quote_line_item, api_client.update_quote_line_item, api_client.remove_quote_line_item,
            None, parent=self,
        )
        if dialog.exec():
            self._load_quote()

    def _on_line_item_double_clicked(self):
        """Opens BillingLineItemDialog in edit mode for the double-clicked row; reloads the quote if changed."""
        selected_items = self.line_items_table.selectedItems()
        if not selected_items:
            return

        line_item = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = BillingLineItemDialog(
            self.quote_id, self.services,
            api_client.add_quote_line_item, api_client.update_quote_line_item, api_client.remove_quote_line_item,
            line_item, parent=self,
        )
        if dialog.exec():
            self._load_quote()

    # -----------------------------------------------------------------
    # Discount / Tax
    # -----------------------------------------------------------------
    def _on_discount_changed(self):
        """Applies the newly-selected discount immediately."""
        discount_id = self.discount_combo.currentData()
        try:
            self.quote = api_client.update_quote(self.quote_id, {"discount_id": discount_id})
        except ApiError as e:
            QMessageBox.critical(self, "Update Failed", str(e))
            return
        self._render_line_items()
        self._render_totals()

    def _on_tax_changed(self):
        """Applies the newly-selected tax rate immediately."""
        tax_rate_id = self.tax_combo.currentData()
        try:
            self.quote = api_client.update_quote(self.quote_id, {"tax_rate_id": tax_rate_id})
        except ApiError as e:
            QMessageBox.critical(self, "Update Failed", str(e))
            return
        self._render_line_items()
        self._render_totals()

    # -----------------------------------------------------------------
    # Conversion
    # -----------------------------------------------------------------
    def _on_convert_to_invoice(self):
        """Converts this quote into a real invoice, after confirmation."""
        if not self.quote.get("line_items"):
            QMessageBox.information(self, "No Line Items", "Add at least one line item before converting to an invoice.")
            return

        confirmed = QMessageBox.question(
            self,
            "Convert to Invoice",
            f"Convert this quote (total ${self.quote['total']}) into an invoice? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        try:
            api_client.convert_quote_to_invoice(self.quote_id)
        except ApiError as e:
            QMessageBox.critical(self, "Conversion Failed", str(e))
            return

        self.converted = True
        self._load_quote()
