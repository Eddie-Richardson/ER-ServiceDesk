# ER-ServiceDesk/desktop/tickets_window.py

"""
Tickets window: list view with filters, plus create/edit.

Filtering starts as single-select dropdowns per column (Category, Status,
Priority) -- the foundation this is built on (fetch, table, the New/Edit
form) doesn't change if that later grows into Excel-style multi-select
checkbox filters. That upgrade is a swap of the filter widgets and
matching logic, not a rebuild of this window.
"""

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.ticket_form_dialog import PRIORITY_LEVELS, TicketFormDialog
from desktop.tickets_worker import TicketsDataWorker

ANY_FILTER = "Any"
COLUMN_HEADERS = ["ID", "Title", "Customer", "Category", "Status", "Priority"]


class TicketsWindow(QWidget):
    """Standalone window listing all tickets, with filtering and create/edit."""

    def __init__(self):
        """Builds the toolbar, filter row, and table, then loads data."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Tickets")
        self.resize(820, 520)

        self._thread: QThread | None = None
        self._worker: TicketsDataWorker | None = None
        self.reference_data: dict = {}
        self.all_tickets: list[dict] = []

        self._build_ui()
        self._load_data()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds the toolbar, filter row, table, and status label."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_MD)

        title = QLabel("Tickets")
        title.setObjectName("title")
        outer_layout.addWidget(title)

        outer_layout.addLayout(self._build_toolbar())
        outer_layout.addLayout(self._build_filter_row())

        self.status_label = QLabel("Loading tickets...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    def _build_toolbar(self) -> QHBoxLayout:
        """
        Returns:
            A layout containing the New Ticket and Refresh buttons.
        """
        toolbar = QHBoxLayout()

        new_ticket_button = QPushButton("New Ticket")
        new_ticket_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_ticket_button.clicked.connect(self._open_new_ticket_dialog)
        toolbar.addWidget(new_ticket_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)

        toolbar.addStretch()
        return toolbar

    def _build_filter_row(self) -> QHBoxLayout:
        """
        Returns:
            A layout containing the Category/Status/Priority filter
            dropdowns. Populated once reference data loads.
        """
        filter_row = QHBoxLayout()
        filter_row.setSpacing(layout.SPACE_SM)

        self.category_filter = QComboBox()
        self.category_filter.currentIndexChanged.connect(self._apply_filters)
        self.status_filter = QComboBox()
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        self.priority_filter = QComboBox()
        self.priority_filter.addItem(ANY_FILTER)
        self.priority_filter.addItems(PRIORITY_LEVELS)
        self.priority_filter.currentIndexChanged.connect(self._apply_filters)

        for label_text, combo in [
            ("Category", self.category_filter),
            ("Status", self.status_filter),
            ("Priority", self.priority_filter),
        ]:
            filter_row.addWidget(QLabel(label_text))
            filter_row.addWidget(combo)

        filter_row.addStretch()
        return filter_row

    # -----------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------
    def _load_data(self):
        """Starts a background fetch of tickets and every reference table."""
        self.status_label.setText("Loading tickets...")
        self.table.setRowCount(0)

        self._thread = QThread()
        self._worker = TicketsDataWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_data_loaded(self, success: bool, result):
        """
        Handles the background load's result: populates the filter
        dropdowns and table on success, or shows an error on failure.

        Args:
            success: Whether the load succeeded.
            result: On success, the reference_data dict from
                TicketsDataWorker. On failure, a human-readable error
                message string.
        """
        if not success:
            self.status_label.setText(f"Couldn't load tickets: {result}")
            return

        self.reference_data = result
        self.all_tickets = result["tickets"]

        self._populate_lookup_filter(self.category_filter, result["categories"])
        self._populate_lookup_filter(self.status_filter, result["statuses"])

        self._apply_filters()

    def _populate_lookup_filter(self, combo: QComboBox, records: list[dict]):
        """
        Fills a filter dropdown with "Any" plus every record's name,
        storing each record's id as the item's userData for filtering.

        Args:
            combo: The filter combo box to populate.
            records: Lookup records (each with "id" and "name") to list.
        """
        combo.blockSignals(True)
        combo.clear()
        combo.addItem(ANY_FILTER, userData=None)
        for record in records:
            combo.addItem(record["name"], userData=record["id"])
        combo.blockSignals(False)

    # -----------------------------------------------------------------
    # Filtering + table rendering
    # -----------------------------------------------------------------
    def _apply_filters(self):
        """Re-renders the table with the current Category/Status/Priority filters applied."""
        category_id = self.category_filter.currentData()
        status_id = self.status_filter.currentData()
        priority = self.priority_filter.currentText()

        filtered = self.all_tickets
        if category_id is not None:
            filtered = [t for t in filtered if t["category_id"] == category_id]
        if status_id is not None:
            filtered = [t for t in filtered if t["status_id"] == status_id]
        if priority != ANY_FILTER:
            filtered = [t for t in filtered if t.get("priority") == priority]

        self._render_table(filtered)
        self.status_label.setText(
            f"Showing {len(filtered)} of {len(self.all_tickets)} ticket(s)."
        )

    def _render_table(self, tickets: list[dict]):
        """
        Args:
            tickets: The tickets to display, already filtered.
        """
        self.table.setRowCount(len(tickets))
        customers_by_id = {c["id"]: c for c in self.reference_data.get("customers", [])}
        categories_by_id = {c["id"]: c["name"] for c in self.reference_data.get("categories", [])}
        statuses_by_id = {s["id"]: s["name"] for s in self.reference_data.get("statuses", [])}

        for row, ticket in enumerate(tickets):
            customer = customers_by_id.get(ticket["customer_id"])
            customer_label = (
                f"{customer['first_name']} {customer['last_name']}" if customer else "-"
            )

            values = [
                str(ticket["id"]),
                ticket.get("title", ""),
                customer_label,
                categories_by_id.get(ticket["category_id"], "-"),
                statuses_by_id.get(ticket["status_id"], "-"),
                ticket.get("priority", "-"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, ticket)
                self.table.setItem(row, col, item)

    # -----------------------------------------------------------------
    # Create / edit
    # -----------------------------------------------------------------
    def _open_new_ticket_dialog(self):
        """Opens the ticket form in create mode; refreshes the list if a ticket was saved."""
        dialog = TicketFormDialog(self.reference_data, ticket=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Opens the ticket form pre-filled with the double-clicked row's ticket."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        ticket = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = TicketFormDialog(self.reference_data, ticket=ticket, parent=self)
        if dialog.exec():
            self._load_data()
