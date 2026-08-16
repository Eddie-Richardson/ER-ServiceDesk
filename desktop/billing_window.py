# ER-ServiceDesk/desktop/billing_window.py

"""
Standalone Billing window -- lists every quote and invoice across the
whole business, not scoped to a single ticket (see billing_dialog.py
for that per-ticket view, reached from a ticket's own "Billing"
button). This is the main-window nav entry point for billing, the
same role TicketsWindow/InventoryWindow/CustomersWindow play for their
own areas.

Filterable by customer and, for invoices, paid status. Double-clicking
a row opens the exact same QuoteDetailDialog/InvoiceDetailDialog
already used from the per-ticket view -- one detail screen either way,
just two different entry points into it.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.invoice_detail_dialog import InvoiceDetailDialog
from desktop.quote_detail_dialog import QuoteDetailDialog
from desktop.window_geometry import restore_geometry, save_geometry

QUOTE_COLUMN_HEADERS = ["Quote #", "Customer", "Ticket #", "Total", "Status"]
INVOICE_COLUMN_HEADERS = ["Invoice #", "Customer", "Ticket #", "Total", "Paid"]
PAID_FILTER_OPTIONS = ["All", "Paid", "Unpaid"]


class BillingWindow(QWidget):
    """Standalone window listing every quote and invoice across the business."""

    window_closed = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Billing")
        self.resize(860, 560)
        restore_geometry(self, "BillingWindow")

        self.customers: list[dict] = []
        self.tickets_by_id: dict[int, dict] = {}
        self.customers_by_id: dict[int, dict] = {}
        self.all_quotes: list[dict] = []
        self.all_invoices: list[dict] = []

        self._build_ui()
        self._load_data()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "BillingWindow")
        super().closeEvent(event)
        self.window_closed.emit()

    def _build_ui(self):
        """Builds the title, filter row, Quotes section, and Invoices section."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_MD)

        title = QLabel("Billing")
        title.setObjectName("title")
        outer_layout.addWidget(title)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel("Customer:"))
        self.customer_filter = QComboBox()
        self.customer_filter.addItem("All Customers", userData=None)
        self.customer_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.customer_filter)

        filter_row.addWidget(QLabel("Invoice Paid Status:"))
        self.paid_filter = QComboBox()
        self.paid_filter.addItems(PAID_FILTER_OPTIONS)
        self.paid_filter.currentIndexChanged.connect(self._apply_filters)
        filter_row.addWidget(self.paid_filter)
        filter_row.addStretch()
        outer_layout.addLayout(filter_row)

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        quotes_label = QLabel("Quotes")
        quotes_label.setObjectName("subtitle")
        outer_layout.addWidget(quotes_label)

        self.quotes_table = QTableWidget()
        self.quotes_table.setColumnCount(len(QUOTE_COLUMN_HEADERS))
        self.quotes_table.setHorizontalHeaderLabels(QUOTE_COLUMN_HEADERS)
        self.quotes_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.quotes_table.verticalHeader().setVisible(False)
        self.quotes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quotes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quotes_table.doubleClicked.connect(self._on_quote_double_clicked)
        outer_layout.addWidget(self.quotes_table)

        invoices_label = QLabel("Invoices")
        invoices_label.setObjectName("subtitle")
        outer_layout.addWidget(invoices_label)

        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(len(INVOICE_COLUMN_HEADERS))
        self.invoices_table.setHorizontalHeaderLabels(INVOICE_COLUMN_HEADERS)
        self.invoices_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.invoices_table.verticalHeader().setVisible(False)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.doubleClicked.connect(self._on_invoice_double_clicked)
        outer_layout.addWidget(self.invoices_table)

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------
    def _load_data(self):
        """Fetches customers, tickets, quotes, and invoices, then populates the customer filter and renders both tables."""
        self.status_label.setText("Loading...")
        try:
            self.customers = api_client.list_customers()
            tickets = api_client.list_tickets()
            self.all_quotes = api_client.list_quotes()
            self.all_invoices = api_client.list_invoices()
        except ApiError as e:
            self.status_label.setText(f"Couldn't load billing data: {e}")
            return

        self.customers_by_id = {c["id"]: c for c in self.customers}
        self.tickets_by_id = {t["id"]: t for t in tickets}

        self.customer_filter.blockSignals(True)
        current_selection = self.customer_filter.currentData()
        self.customer_filter.clear()
        self.customer_filter.addItem("All Customers", userData=None)
        for customer in sorted(self.customers, key=lambda c: f"{c['first_name']} {c['last_name']}"):
            label = f"{customer['first_name']} {customer['last_name']}"
            self.customer_filter.addItem(label, userData=customer["id"])
        restored_index = self.customer_filter.findData(current_selection)
        self.customer_filter.setCurrentIndex(restored_index if restored_index >= 0 else 0)
        self.customer_filter.blockSignals(False)

        self._apply_filters()

    def _customer_name_for_ticket(self, ticket_id: int) -> str:
        """
        Args:
            ticket_id: The ticket to look up the owning customer's name for.

        Returns:
            "First Last", or "Unknown" if the ticket or customer can't
            be found (e.g. stale data mid-refresh).
        """
        ticket = self.tickets_by_id.get(ticket_id)
        if not ticket:
            return "Unknown"
        customer = self.customers_by_id.get(ticket.get("customer_id"))
        if not customer:
            return "Unknown"
        return f"{customer['first_name']} {customer['last_name']}"

    def _customer_id_for_ticket(self, ticket_id: int) -> int | None:
        """
        Args:
            ticket_id: The ticket to look up the owning customer's id for.

        Returns:
            The customer id, or None if the ticket can't be found.
        """
        ticket = self.tickets_by_id.get(ticket_id)
        return ticket.get("customer_id") if ticket else None

    # -----------------------------------------------------------------
    # Filtering / rendering
    # -----------------------------------------------------------------
    def _apply_filters(self):
        """Re-renders both tables filtered to the current customer/paid-status selections."""
        selected_customer_id = self.customer_filter.currentData()
        paid_filter = self.paid_filter.currentText()

        filtered_quotes = [
            q for q in self.all_quotes
            if selected_customer_id is None or self._customer_id_for_ticket(q["ticket_id"]) == selected_customer_id
        ]
        filtered_invoices = [
            i for i in self.all_invoices
            if selected_customer_id is None or self._customer_id_for_ticket(i["ticket_id"]) == selected_customer_id
        ]
        if paid_filter == "Paid":
            filtered_invoices = [i for i in filtered_invoices if i.get("is_paid")]
        elif paid_filter == "Unpaid":
            filtered_invoices = [i for i in filtered_invoices if not i.get("is_paid")]

        self._render_quotes(filtered_quotes)
        self._render_invoices(filtered_invoices)
        self.status_label.setText(f"{len(filtered_quotes)} quote(s), {len(filtered_invoices)} invoice(s).")

    def _render_quotes(self, quotes: list[dict]):
        """
        Args:
            quotes: The quotes to display, already filtered.
        """
        self.quotes_table.setRowCount(len(quotes))
        for row, quote in enumerate(quotes):
            status = f"Converted to Invoice #{quote['converted_invoice_id']}" if quote.get("converted_invoice_id") else "Open"
            values = [
                f"#{quote['id']}",
                self._customer_name_for_ticket(quote["ticket_id"]),
                f"#{quote['ticket_id']}",
                f"${quote['total']}",
                status,
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, quote)
                self.quotes_table.setItem(row, col, cell)

    def _render_invoices(self, invoices: list[dict]):
        """
        Args:
            invoices: The invoices to display, already filtered.
        """
        self.invoices_table.setRowCount(len(invoices))
        for row, invoice in enumerate(invoices):
            values = [
                f"#{invoice['id']}",
                self._customer_name_for_ticket(invoice["ticket_id"]),
                f"#{invoice['ticket_id']}",
                f"${invoice['total']}",
                "Yes" if invoice.get("is_paid") else "No",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, invoice)
                self.invoices_table.setItem(row, col, cell)

    # -----------------------------------------------------------------
    # Opening detail screens
    # -----------------------------------------------------------------
    def _on_quote_double_clicked(self):
        """Opens the double-clicked quote's detail screen; refreshes on close."""
        selected_items = self.quotes_table.selectedItems()
        if not selected_items:
            return
        quote = selected_items[0].data(Qt.ItemDataRole.UserRole)
        ticket = self.tickets_by_id.get(quote["ticket_id"], {})
        dialog = QuoteDetailDialog(quote["id"], quote["ticket_id"], ticket.get("title", "Ticket"), parent=self)
        dialog.exec()
        self._load_data()

    def _on_invoice_double_clicked(self):
        """Opens the double-clicked invoice's detail screen; refreshes on close."""
        selected_items = self.invoices_table.selectedItems()
        if not selected_items:
            return
        invoice = selected_items[0].data(Qt.ItemDataRole.UserRole)
        ticket = self.tickets_by_id.get(invoice["ticket_id"], {})
        dialog = InvoiceDetailDialog(invoice["id"], invoice["ticket_id"], ticket.get("title", "Ticket"), parent=self)
        dialog.exec()
        self._load_data()
