# ER-ServiceDesk/desktop/tickets_window.py

"""
Tickets window: list view with filters, plus create/edit.

Filtering uses Excel-style multi-select checklist popups per column
(Category, Status, Priority) -- select zero or more values per column,
and rows matching any selected value in each filtered column are shown.
This sits on the same foundation (fetch, table, the New/Edit form) as
the single-select version it replaced; only the filter widgets
(MultiSelectFilterButton) and the matching logic changed.

Default view excludes Closed tickets (nothing left to track -- payment
received, device gone) but includes Resolved (repair done, still needs
follow-up for pickup/payment), sorted Urgent-to-Low by default. Every
column header is clickable to sort ascending/descending.

Can be opened pre-filtered to a single status via initial_status_filter,
which is how the Dashboard's status cards open this window scoped to
whatever was clicked.

The table's automatic row-number gutter is hidden -- with a real ID
column present, showing both would put two different numbers on screen
that look similar but mean different things (visual position vs. the
ticket's actual permanent identifier), which invites confusing the two.

Emits window_closed so callers (the Dashboard's nav button) can tell
when this window has actually closed, e.g. to un-highlight a nav button
that should only stay lit while the window is genuinely open.
"""

from PySide6.QtCore import QThread, Qt, Signal
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

from desktop import layout, session
from desktop.multi_select_filter import MultiSelectFilterButton
from desktop.ticket_form_dialog import PRIORITY_LEVELS, TicketFormDialog
from desktop.tickets_worker import TicketsDataWorker

COLUMN_HEADERS = ["ID", "Title", "Customer", "Category", "Status", "Priority", "Assigned To", "Location"]
PRIORITY_RANK = {"Urgent": 0, "High": 1, "Medium": 2, "Low": 3}
DEFAULT_SORT_COLUMN = 5  # Priority
CLOSED_STATUS_NAME = "Closed"


class TicketsWindow(QWidget):
    """Standalone window listing all tickets, with filtering and create/edit."""

    window_closed = Signal()

    def __init__(self, initial_status_filter: str | None = None):
        """
        Args:
            initial_status_filter: If given, the window opens pre-filtered
                to just this status name (e.g. "Open"), instead of the
                default "everything except Closed" view. Used by the
                Dashboard's status cards.
        """
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Tickets")
        self.resize(860, 520)

        self._thread: QThread | None = None
        self._worker: TicketsDataWorker | None = None
        self.reference_data: dict = {}
        self.all_tickets: list[dict] = []
        self.initial_status_filter = initial_status_filter
        self.sort_column = DEFAULT_SORT_COLUMN
        self.sort_ascending = True

        self._build_ui()
        self._load_data()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        super().closeEvent(event)
        self.window_closed.emit()

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
        self.table.verticalHeader().setVisible(False)  # redundant with the ID column; see module docstring
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        self.table.horizontalHeader().sectionClicked.connect(self._on_header_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)
        self._update_header_labels()

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
        self._apply_default_status_filter(result["statuses"])

        self._apply_filters()

    def _apply_default_status_filter(self, statuses: list[dict]):
        """
        Sets the status filter's initial checked set: either the single
        status requested via initial_status_filter (e.g. from a
        Dashboard status card), or -- absent that -- every status except
        Closed, since a Closed ticket has nothing left to track.

        Args:
            statuses: The full list of status records just loaded.
        """
        if self.initial_status_filter is not None:
            matching = [s["id"] for s in statuses if s["name"] == self.initial_status_filter]
            self.status_filter.set_checked_ids(set(matching))
            return

        default_ids = {s["id"] for s in statuses if s["name"] != CLOSED_STATUS_NAME}
        self.status_filter.set_checked_ids(default_ids)

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

        filtered = self._sort_tickets(filtered)
        self._render_table(filtered)
        self.status_label.setText(
            f"Showing {len(filtered)} of {len(self.all_tickets)} ticket(s)."
        )

    def _on_header_clicked(self, column: int):
        """
        Toggles ascending/descending if the same column is clicked again,
        otherwise switches to sorting by the newly clicked column
        ascending. Re-renders with the new sort applied.

        Args:
            column: The clicked column's index.
        """
        if column == self.sort_column:
            self.sort_ascending = not self.sort_ascending
        else:
            self.sort_column = column
            self.sort_ascending = True
        self._update_header_labels()
        self._apply_filters()

    def _update_header_labels(self):
        """Adds a sort-direction arrow to whichever column header is currently sorted."""
        arrow = " \u25b2" if self.sort_ascending else " \u25bc"
        labels = list(COLUMN_HEADERS)
        labels[self.sort_column] = labels[self.sort_column] + arrow
        self.table.setHorizontalHeaderLabels(labels)

    def _sort_tickets(self, tickets: list[dict]) -> list[dict]:
        """
        Args:
            tickets: The filtered tickets to sort.

        Returns:
            The same tickets, sorted by the current sort column/direction.
        """
        categories_by_id = {c["id"]: c["name"] for c in self.reference_data.get("categories", [])}
        statuses_by_id = {s["id"]: s["name"] for s in self.reference_data.get("statuses", [])}
        customers_by_id = {c["id"]: c for c in self.reference_data.get("customers", [])}

        def sort_key(ticket: dict):
            column = self.sort_column
            if column == 0:
                return ticket["id"]
            if column == 1:
                return ticket.get("title", "").lower()
            if column == 2:
                customer = customers_by_id.get(ticket["customer_id"])
                name = f"{customer['first_name']} {customer['last_name']}" if customer else ""
                return name.lower()
            if column == 3:
                return categories_by_id.get(ticket["category_id"], "").lower()
            if column == 4:
                return statuses_by_id.get(ticket["status_id"], "").lower()
            if column == 5:
                return PRIORITY_RANK.get(ticket.get("priority"), len(PRIORITY_RANK))
            if column == 6:
                return self._assigned_to_label(ticket.get("assigned_to")).lower()
            if column == 7:
                return self._location_label(ticket.get("current_location_id")).lower()
            return 0

        return sorted(tickets, key=sort_key, reverse=not self.sort_ascending)

    def _assigned_to_label(self, assigned_to) -> str:
        """
        Resolves an assigned_to id to a display name.

        Args:
            assigned_to: The ticket's assigned_to field (a user id, or None).

        Returns:
            "Unassigned", "Me", the resolved technician's name (only
            possible for superuser sessions, which have the full user
            list), or a generic "Assigned" fallback when the name can't
            be resolved.
        """
        if assigned_to is None:
            return "Unassigned"
        if assigned_to == session.current_user_id():
            return "Me"
        for user in self.reference_data.get("users", []):
            if user["id"] == assigned_to:
                return user["full_name"]
        return "Assigned"

    def _location_label(self, location_id) -> str:
        """
        Resolves a current_location_id to a display name.

        Args:
            location_id: The ticket's current_location_id field (a
                Location id, or None).

        Returns:
            The location's name, or "-" if unset/unresolvable.
        """
        if location_id is None:
            return "-"
        for location in self.reference_data.get("locations", []):
            if location["id"] == location_id:
                return location["name"]
        return "-"

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
                self._assigned_to_label(ticket.get("assigned_to")),
                self._location_label(ticket.get("current_location_id")),
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
