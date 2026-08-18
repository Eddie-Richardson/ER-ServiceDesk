# ER-ServiceDesk/desktop/invoice_detail_dialog.py

"""
Dialog for viewing and managing a single invoice -- its line items,
discount/tax selection, computed totals, payment history, and payment
plan.

Line items and discount/tax follow the exact same pattern as
QuoteDetailDialog. Payments and payment plans are the invoice-specific
pieces on top of that.
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
from desktop.installment_action_dialog import InstallmentActionDialog
from desktop.payment_dialog import PaymentDialog
from desktop.payment_plan_setup_dialog import PaymentPlanSetupDialog
from desktop.window_geometry import restore_geometry, save_geometry

LINE_ITEM_COLUMN_HEADERS = ["Service", "Qty", "Unit Price", "Line Total"]
INSTALLMENT_COLUMN_HEADERS = ["#", "Due Date", "Amount", "Status"]


class InvoiceDetailDialog(QDialog):
    """Modal dialog for viewing and managing a single invoice."""

    def __init__(self, invoice_id: int, ticket_id: int, ticket_title: str, parent=None):
        """
        Args:
            ticket_id: The ticket this invoice bills for, shown for
                traceability back to the job.
            ticket_title: Shown in the window title for context.
        """
        super().__init__(parent)
        self.invoice_id = invoice_id
        self.ticket_id = ticket_id
        self.invoice: dict | None = None
        self.services: list[dict] = []
        self.parts: list[dict] = []
        self.payments: list[dict] = []
        self.payment_plan: dict | None = None

        self.setWindowTitle(f"Invoice - {ticket_title}")
        self.resize(600, 700)
        restore_geometry(self, "InvoiceDetailDialog")

        self._build_ui()
        self._load_services()
        self._load_invoice()

    def closeEvent(self, event):
        save_geometry(self, "InvoiceDetailDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds every section: ticket reference, line items, discount/tax, totals, payments, and payment plan."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.ticket_ref_label = QLabel(f"Ticket #{self.ticket_id}")
        self.ticket_ref_label.setObjectName("subtitle")
        outer_layout.addWidget(self.ticket_ref_label)

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
        self.line_items_table.setFixedHeight(120)
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

        self.paid_status_label = QLabel("")
        outer_layout.addWidget(self.paid_status_label)

        self.send_button = QPushButton("Send Invoice")
        self.send_button.setObjectName("secondary")
        self.send_button.clicked.connect(self._on_send_invoice)
        outer_layout.addWidget(self.send_button)

        self.send_status_label = QLabel("")
        self.send_status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.send_status_label)

        payments_label = QLabel("Payments")
        payments_label.setObjectName("subtitle")
        outer_layout.addWidget(payments_label)

        self.record_payment_button = QPushButton("Record Payment")
        self.record_payment_button.clicked.connect(self._on_record_payment)
        outer_layout.addWidget(self.record_payment_button)

        self.payments_label_display = QLabel("No payments yet.")
        self.payments_label_display.setWordWrap(True)
        outer_layout.addWidget(self.payments_label_display)

        plan_label = QLabel("Payment Plan")
        plan_label.setObjectName("subtitle")
        outer_layout.addWidget(plan_label)

        self.setup_plan_button = QPushButton("Set Up Payment Plan")
        self.setup_plan_button.setObjectName("secondary")
        self.setup_plan_button.clicked.connect(self._on_setup_payment_plan)
        outer_layout.addWidget(self.setup_plan_button)

        self.plan_status_label = QLabel("")
        self.plan_status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.plan_status_label)

        self.installments_table = QTableWidget()
        self.installments_table.setColumnCount(len(INSTALLMENT_COLUMN_HEADERS))
        self.installments_table.setHorizontalHeaderLabels(INSTALLMENT_COLUMN_HEADERS)
        self.installments_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.installments_table.verticalHeader().setVisible(False)
        self.installments_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.installments_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.installments_table.doubleClicked.connect(self._on_installment_double_clicked)
        self.installments_table.setFixedHeight(150)
        self.installments_table.hide()
        outer_layout.addWidget(self.installments_table)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------
    def _load_services(self):
        """Loads every active service and every priced part for the line-item picker."""
        try:
            all_services = api_client.list_services()
        except ApiError:
            all_services = []
        self.services = [s for s in all_services if s.get("is_active", True)]

        try:
            all_parts = api_client.list_parts()
        except ApiError:
            all_parts = []
        self.parts = [p for p in all_parts if p.get("selling_price") is not None]

    def _load_invoice(self):
        """Fetches the invoice and every related section, then refreshes the display."""
        try:
            self.invoice = api_client.get_invoice(self.invoice_id)
        except ApiError as e:
            QMessageBox.critical(self, "Load Failed", str(e))
            return

        try:
            self.payments = api_client.list_payments_for_invoice(self.invoice_id)
        except ApiError:
            self.payments = []

        self._populate_discount_tax_pickers()
        self._render_line_items()
        self._render_totals()
        self._render_send_status()
        self._render_payments()
        self._load_payment_plan()

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
        current_discount_id = self.invoice.get("discount_id")
        for d in discounts:
            if d.get("is_active", True) or d["id"] == current_discount_id:
                self.discount_combo.addItem(f"{d['name']} ({d['percentage']}%)", userData=d["id"])
        idx = self.discount_combo.findData(current_discount_id)
        self.discount_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.discount_combo.blockSignals(False)

        self.tax_combo.blockSignals(True)
        self.tax_combo.clear()
        self.tax_combo.addItem("None", userData=None)
        current_tax_id = self.invoice.get("tax_rate_id")
        for t in tax_rates:
            if t.get("is_active", True) or t["id"] == current_tax_id:
                self.tax_combo.addItem(f"{t['name']} ({t['percentage']}%)", userData=t["id"])
        idx = self.tax_combo.findData(current_tax_id)
        self.tax_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.tax_combo.blockSignals(False)

    def _render_line_items(self):
        """Renders the invoice's current line items into the table."""
        line_items = self.invoice.get("line_items", [])
        self.line_items_table.setRowCount(len(line_items))
        for row, item in enumerate(line_items):
            line_total = float(item["unit_price"]) * item["quantity"]
            values = [
                item["service_name"] or item["part_name"],
                str(item["quantity"]),
                f"${item['unit_price']}",
                f"${line_total:.2f}",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item)
                self.line_items_table.setItem(row, col, cell)

    def _render_totals(self):
        """Renders the Subtotal/Discount/Tax/Total summary and paid status."""
        self.totals_label.setText(
            f"Subtotal: ${self.invoice['subtotal']}   "
            f"Discount: -${self.invoice['discount_amount']}   "
            f"Tax: +${self.invoice['tax_amount']}   "
            f"Total: ${self.invoice['total']}"
        )
        if self.invoice.get("is_paid"):
            self.paid_status_label.setText("PAID IN FULL")
        else:
            self.paid_status_label.setText(f"Balance due: ${self._remaining_balance():.2f}")

    def _render_send_status(self):
        """Shows whether this invoice has ever been emailed, and when."""
        sent_at = self.invoice.get("invoice_sent_at")
        if sent_at:
            self.send_status_label.setText(f"Invoice sent on {sent_at[:10]}.")
        else:
            self.send_status_label.setText("Invoice not yet sent.")

    def _render_payments(self):
        """Renders the payment history list."""
        if not self.payments:
            self.payments_label_display.setText("No payments yet.")
            return

        lines = [f"${p['amount']} ({p['method']}) on {p['created_at'][:10]}" for p in self.payments]
        self.payments_label_display.setText("\n".join(lines))

    def _total_paid(self) -> float:
        """
        Returns:
            The sum of every payment recorded against this invoice so far.
        """
        return sum(float(p["amount"]) for p in self.payments)

    def _remaining_balance(self) -> float:
        """
        Returns:
            The invoice's total minus payments recorded so far --
            correctly reflects a partial payment, not just the binary
            paid/unpaid state.
        """
        remaining = float(self.invoice["total"]) - self._total_paid()
        return max(remaining, 0.0)

    # -----------------------------------------------------------------
    # Line items
    # -----------------------------------------------------------------
    def _on_add_line_item(self):
        """Opens BillingLineItemDialog in add mode; reloads the invoice if a line item was added."""
        if not self.services and not self.parts:
            QMessageBox.information(self, "No Billable Items", "No active services or priced parts are configured yet -- add one in Settings/Inventory first.")
            return

        dialog = BillingLineItemDialog(
            self.invoice_id, self.services,
            api_client.add_invoice_line_item, api_client.update_invoice_line_item, api_client.remove_invoice_line_item,
            None, parent=self, parts=self.parts,
        )
        if dialog.exec():
            self._load_invoice()

    def _on_line_item_double_clicked(self):
        """Opens BillingLineItemDialog in edit mode for the double-clicked row; reloads the invoice if changed."""
        selected_items = self.line_items_table.selectedItems()
        if not selected_items:
            return

        line_item = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = BillingLineItemDialog(
            self.invoice_id, self.services,
            api_client.add_invoice_line_item, api_client.update_invoice_line_item, api_client.remove_invoice_line_item,
            line_item, parent=self, parts=self.parts,
        )
        if dialog.exec():
            self._load_invoice()

    # -----------------------------------------------------------------
    # Discount / Tax
    # -----------------------------------------------------------------
    def _on_discount_changed(self):
        """Applies the newly-selected discount immediately."""
        discount_id = self.discount_combo.currentData()
        try:
            self.invoice = api_client.update_invoice(self.invoice_id, {"discount_id": discount_id})
        except ApiError as e:
            QMessageBox.critical(self, "Update Failed", str(e))
            return
        self._render_line_items()
        self._render_totals()

    def _on_tax_changed(self):
        """Applies the newly-selected tax rate immediately."""
        tax_rate_id = self.tax_combo.currentData()
        try:
            self.invoice = api_client.update_invoice(self.invoice_id, {"tax_rate_id": tax_rate_id})
        except ApiError as e:
            QMessageBox.critical(self, "Update Failed", str(e))
            return
        self._render_line_items()
        self._render_totals()

    # -----------------------------------------------------------------
    # Sending
    # -----------------------------------------------------------------
    def _on_send_invoice(self):
        """Emails this invoice to the customer, after confirmation. Blocks sending an empty invoice. Deliberately allowed even when is_paid -- re-sending serves as a receipt."""
        if not self.invoice.get("line_items"):
            QMessageBox.information(self, "No Line Items", "Add at least one line item before sending this invoice.")
            return

        confirmed = QMessageBox.question(
            self,
            "Send Invoice",
            f"Email this invoice (total ${self.invoice['total']}) to the customer?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        try:
            api_client.send_invoice(self.invoice_id)
        except ApiError as e:
            QMessageBox.critical(self, "Send Failed", str(e))
            return

        self._load_invoice()

    # -----------------------------------------------------------------
    # Payments
    # -----------------------------------------------------------------
    def _on_record_payment(self):
        """Opens PaymentDialog; reloads the invoice if a payment was recorded."""
        dialog = PaymentDialog(self.invoice_id, self._remaining_balance(), parent=self)
        if dialog.exec():
            self._load_invoice()

    # -----------------------------------------------------------------
    # Payment plan
    # -----------------------------------------------------------------
    def _load_payment_plan(self):
        """Fetches this invoice's payment plan, if any, and renders it."""
        try:
            self.payment_plan = api_client.get_payment_plan_by_invoice(self.invoice_id)
        except ApiError:
            self.payment_plan = None

        has_plan = self.payment_plan is not None
        self.setup_plan_button.setVisible(not has_plan and not self.invoice.get("is_paid"))
        self.installments_table.setVisible(has_plan)

        if has_plan:
            self.plan_status_label.setText(
                f"{self.payment_plan['frequency'].capitalize()} plan, "
                f"${self.payment_plan['installment_amount']} per installment -- {self.payment_plan['status']}."
            )
            self._render_installments()
        else:
            self.plan_status_label.setText("")

    def _render_installments(self):
        """Renders the payment plan's installments into the table."""
        installments = self.payment_plan.get("installments", [])
        self.installments_table.setRowCount(len(installments))
        for row, installment in enumerate(installments):
            status = "Paid" if installment.get("payment_id") else "Pending"
            values = [
                str(installment["sequence_number"]),
                installment["due_date"],
                f"${installment['planned_amount']}",
                status,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, installment)
                self.installments_table.setItem(row, col, cell)

    def _on_setup_payment_plan(self):
        """Opens PaymentPlanSetupDialog; reloads the invoice if a plan was created."""
        dialog = PaymentPlanSetupDialog(self.invoice_id, self._remaining_balance(), parent=self)
        if dialog.exec():
            self._load_invoice()

    def _on_installment_double_clicked(self):
        """Opens InstallmentActionDialog for the double-clicked installment; reloads the invoice if it was paid or extended."""
        selected_items = self.installments_table.selectedItems()
        if not selected_items:
            return

        installment = selected_items[0].data(Qt.ItemDataRole.UserRole)
        if installment.get("payment_id"):
            QMessageBox.information(self, "Already Paid", "This installment has already been paid.")
            return

        dialog = InstallmentActionDialog(installment, parent=self)
        dialog.exec()
        if dialog.action_taken:
            self._load_invoice()
