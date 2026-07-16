# ER-ServiceDesk/desktop/tickets_window.py

"""
Tickets window: list view with filters, plus create/edit.

Filtering uses Excel-style multi-select checklist popups per column
(Category, Status, Priority) -- select zero or more values per column,
and rows matching any selected value in each filtered column are shown.
This sits on the same foundation (fetch, table, the New/Edit form) as
the single-select version it replaced; only the filter widgets
(MultiSelectFilterButton) and the matching logic changed.
"""

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
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
from desktop.multi_select_filter import MultiSelectFilterButton
from desktop.ticket_form_dialog import PRIORITY_LEVELS, TicketFormDialog
from desktop.tickets_worker import TicketsDataWorker

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
            A layout containing the Category/Status/Priority multi-select
            filter buttons. Options are populated once reference data
            loads; Priority's options are static since it's a fixed list.
        """
        filter_row = QHBoxLayout()
        filter_row.setSpacing(layout.SPACE_SM)

        self.category_filter = MultiSelectFilterButton("Category")
        self.category_filter.selection_changed.connect(self._apply_filters)
        self.status_filter = MultiSelectFilterButton("Status")
        self.status_filter.selection_changed.connect(self._apply_filters)
        self.priority_filter = MultiSelectFilterButton("Priority")
        self.priority_filter.set_options([(p, p) for p in PRIORITY_LEVELS])
        self.priority_filter.selection_changed.connect(self._apply_filters)

        for filter_button in [self.category_filter, self.status_filter, self.priority_filter]:
            filter_row.addWidget(filter_button)

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

        self.category_filter.set_options(
            [(c["id"], c["name"]) for c in result["categories"]]
        )
        self.status_filter.set_options(
            [(s["id"], s["name"]) for s in result["statuses"]]
        )

        self._apply_filters()

    # -----------------------------------------------------------------
    # Filtering + table rendering
    # -----------------------------------------------------------------
    def _apply_filters(self):
        """
        Re-renders the table with the current Category/Status/Priority
        filters applied. Each filter's selected_ids() being empty means
        "no filter on this column, show all values" -- otherwise a row
        must match at least one selected value in that column to stay
        visible. The three filters combine with AND (a row must satisfy
        all three), while each filter's own selections combine with OR.
        """
        category_ids = self.category_filter.selected_ids()
        status_ids = self.status_filter.selected_ids()
        priorities = self.priority_filter.selected_ids()

        filtered = self.all_tickets
        if category_ids:
            filtered = [t for t in filtered if t["category_id"] in category_ids]
        if status_ids:
            filtered = [t for t in filtered if t["status_id"] in status_ids]
        if priorities:
            filtered = [t for t in filtered if t.get("priority") in priorities]

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
