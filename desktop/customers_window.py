# ER-ServiceDesk/desktop/customers_window.py

"""
Customers window: searchable list, create, and edit (with a look at
each customer's devices from inside the edit dialog).

Search is a live-filtering text box rather than the type-ahead combo
box style used for the customer picker inside the ticket form -- this
window's whole job is being the full list view, so a plain filter box
above a table fits better than a dropdown-style picker.

Emits window_closed, same as TicketsWindow and InventoryWindow, so the
Dashboard's nav button only stays highlighted while this window is
genuinely open.
"""

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.customer_form_dialog import CustomerFormDialog
from desktop.customers_worker import CustomersDataWorker
from desktop.theme import MONO_FONT_FAMILY

COLUMN_HEADERS = ["Name", "Email", "Phone", "Address"]


class CustomersWindow(QWidget):
    """Standalone window listing all customers, with search, create, and edit."""

    window_closed = Signal()

    def __init__(self):
        """Builds the toolbar, search box, and table, then loads data."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Customers")
        self.resize(760, 520)
        restore_geometry(self, "CustomersWindow")

        self._thread: QThread | None = None
        self._worker: CustomersDataWorker | None = None
        self.all_customers: list[dict] = []
        self.all_devices: list[dict] = []
        self.locations: list[dict] = []

        self._build_ui()
        self._load_data()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "CustomersWindow")
        super().closeEvent(event)
        self.window_closed.emit()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds the toolbar, search box, status label, and table."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_MD)

        title = QLabel("Customers")
        title.setObjectName("title")
        outer_layout.addWidget(title)

        toolbar = QHBoxLayout()
        new_button = QPushButton("New Customer")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_customer_dialog)
        toolbar.addWidget(new_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch()
        outer_layout.addLayout(toolbar)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name or email...")
        self.search_input.setFixedHeight(layout.INPUT_HEIGHT)
        self.search_input.textChanged.connect(self._apply_search)
        outer_layout.addWidget(self.search_input)

        self.status_label = QLabel("Loading customers...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------
    def _load_data(self):
        """Starts a background fetch of customers, devices, and locations."""
        self.status_label.setText("Loading customers...")
        self.table.setRowCount(0)

        self._thread = QThread()
        self._worker = CustomersDataWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_data_loaded(self, success: bool, result):
        """
        Args:
            success: Whether the load succeeded.
            result: On success, the data dict from CustomersDataWorker.
                On failure, a human-readable error message string.
        """
        if not success:
            self.status_label.setText(f"Couldn't load customers: {result}")
            return

        self.all_customers = result["customers"]
        self.all_devices = result["devices"]
        self.locations = result["locations"]
        self._apply_search()

    # -----------------------------------------------------------------
    # Search + table rendering
    # -----------------------------------------------------------------
    def _apply_search(self):
        """Re-renders the table filtered to the current search text, matched against name or email."""
        query = self.search_input.text().strip().lower()

        if not query:
            filtered = self.all_customers
        else:
            filtered = [
                c for c in self.all_customers
                if query in f"{c['first_name']} {c['last_name']}".lower()
                or query in c.get("email", "").lower()
            ]

        self._render_table(filtered)
        self.status_label.setText(
            f"Showing {len(filtered)} of {len(self.all_customers)} customer(s)."
        )

    def _render_table(self, customers: list[dict]):
        """
        Args:
            customers: The customers to display, already filtered.
        """
        mono_font = QFont(MONO_FONT_FAMILY)

        self.table.setRowCount(len(customers))
        for row, customer in enumerate(customers):
            values = [
                f"{customer['first_name']} {customer['last_name']}",
                customer.get("email", ""),
                customer.get("phone") or "-",
                customer.get("address") or "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, customer)

                if col in (1, 2):  # Email, Phone -- technical contact strings, not prose
                    item.setFont(mono_font)

                self.table.setItem(row, col, item)

    # -----------------------------------------------------------------
    # Create / edit
    # -----------------------------------------------------------------
    def _open_new_customer_dialog(self):
        """Opens the customer form in create mode; refreshes the list if a customer was saved."""
        dialog = CustomerFormDialog(None, self.all_devices, self.locations, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Opens the customer form pre-filled with the double-clicked row's customer."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        customer = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = CustomerFormDialog(customer, self.all_devices, self.locations, parent=self)
        if dialog.exec():
            self._load_data()
