# ER-ServiceDesk/desktop/billing_dialog.py

"""
Ticket-level billing screen -- lists every quote and invoice for a
ticket, with a "New Quote" action to start one. Opened from the
ticket form's own "Billing" button, the same pattern as Notes,
History, and Parts.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
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
from desktop.invoice_detail_dialog import InvoiceDetailDialog
from desktop.quote_detail_dialog import QuoteDetailDialog
from desktop.window_geometry import restore_geometry, save_geometry

QUOTE_COLUMN_HEADERS = ["Quote #", "Total", "Status"]
INVOICE_COLUMN_HEADERS = ["Invoice #", "Total", "Paid"]


class BillingDialog(QDialog):
    """Lists every quote and invoice for a ticket."""

    def __init__(self, ticket_id: int, ticket_title: str, parent=None):
        """
        Args:
            ticket_id: The ticket to show billing for.
            ticket_title: Shown in the window title for context.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.ticket_id = ticket_id
        self.ticket_title = ticket_title

        self.setWindowTitle(f"Billing - {ticket_title}")
        self.resize(560, 520)
        restore_geometry(self, "BillingDialog")

        self._build_ui()
        self._load_quotes()
        self._load_invoices()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "BillingDialog")
        super().closeEvent(event)

    def _build_ui(self):
        """Builds the Quotes section and Invoices section."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        quotes_label = QLabel("Quotes")
        quotes_label.setObjectName("subtitle")
        outer_layout.addWidget(quotes_label)

        new_quote_button = QPushButton("New Quote")
        new_quote_button.clicked.connect(self._on_new_quote)
        outer_layout.addWidget(new_quote_button)

        self.quotes_table = QTableWidget()
        self.quotes_table.setColumnCount(len(QUOTE_COLUMN_HEADERS))
        self.quotes_table.setHorizontalHeaderLabels(QUOTE_COLUMN_HEADERS)
        self.quotes_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.quotes_table.verticalHeader().setVisible(False)
        self.quotes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quotes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quotes_table.doubleClicked.connect(self._on_quote_double_clicked)
        self.quotes_table.setFixedHeight(150)
        outer_layout.addWidget(self.quotes_table)

        invoices_label = QLabel("Invoices")
        invoices_label.setObjectName("subtitle")
        outer_layout.addWidget(invoices_label)

        self.invoices_table = QTableWidget()
        self.invoices_table.setColumnCount(len(INVOICE_COLUMN_HEADERS))
        self.invoices_table.setHorizontalHeaderLabels(INVOICE_COLUMN_HEADERS)
        self.invoices_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.invoices_table.verticalHeader().setVisible(False)
        self.invoices_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invoices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.invoices_table.doubleClicked.connect(self._on_invoice_double_clicked)
        self.invoices_table.setFixedHeight(150)
        outer_layout.addWidget(self.invoices_table)

        close_button = QPushButton("Close")
        close_button.setObjectName("secondary")
        close_button.clicked.connect(self.accept)
        outer_layout.addWidget(close_button)

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------
    def _load_quotes(self):
        """Fetches and renders every quote for this ticket."""
        try:
            quotes = api_client.list_quotes_for_ticket(self.ticket_id)
        except ApiError as e:
            QMessageBox.critical(self, "Load Failed", f"Couldn't load quotes: {e}")
            return

        self.quotes_table.setRowCount(len(quotes))
        for row, quote in enumerate(quotes):
            status = f"Converted to Invoice #{quote['converted_invoice_id']}" if quote.get("converted_invoice_id") else "Open"
            values = [f"#{quote['id']}", f"${quote['total']}", status]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, quote)
                self.quotes_table.setItem(row, col, cell)

    def _load_invoices(self):
        """Fetches and renders every invoice for this ticket."""
        try:
            invoices = api_client.list_invoices_for_ticket(self.ticket_id)
        except ApiError as e:
            QMessageBox.critical(self, "Load Failed", f"Couldn't load invoices: {e}")
            return

        self.invoices_table.setRowCount(len(invoices))
        for row, invoice in enumerate(invoices):
            values = [f"#{invoice['id']}", f"${invoice['total']}", "Yes" if invoice.get("is_paid") else "No"]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, invoice)
                self.invoices_table.setItem(row, col, cell)

    # -----------------------------------------------------------------
    # Quotes
    # -----------------------------------------------------------------
    def _on_new_quote(self):
        """Creates a new, empty quote for this ticket, then opens it for line-item entry."""
        try:
            new_quote = api_client.create_quote(self.ticket_id)
        except ApiError as e:
            QMessageBox.critical(self, "Create Failed", str(e))
            return

        self._load_quotes()
        self._open_quote_detail(new_quote["id"])

    def _on_quote_double_clicked(self):
        """Opens the double-clicked quote's detail screen."""
        selected_items = self.quotes_table.selectedItems()
        if not selected_items:
            return
        quote = selected_items[0].data(Qt.ItemDataRole.UserRole)
        self._open_quote_detail(quote["id"])

    def _open_quote_detail(self, quote_id: int):
        """
        Args:
            quote_id: The quote to open.
        """
        dialog = QuoteDetailDialog(quote_id, self.ticket_id, self.ticket_title, parent=self)
        dialog.exec()
        self._load_quotes()
        if dialog.converted:
            self._load_invoices()

    # -----------------------------------------------------------------
    # Invoices
    # -----------------------------------------------------------------
    def _on_invoice_double_clicked(self):
        """Opens the double-clicked invoice's detail screen."""
        selected_items = self.invoices_table.selectedItems()
        if not selected_items:
            return
        invoice = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = InvoiceDetailDialog(invoice["id"], self.ticket_id, self.ticket_title, parent=self)
        dialog.exec()
        self._load_invoices()
