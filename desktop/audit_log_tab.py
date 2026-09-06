# ER-ServiceDesk/desktop/audit_log_tab.py

"""
Settings tab for browsing and filtering the security/compliance audit
trail -- login events, user/role management, ticket and customer
lifecycle, and system-initiated actions like inbound email matching
and outbound notification delivery.

Read-only, matching the backend (see app/routes/audit_logs.py) -- an
audit trail a user could edit through this tab wouldn't be trustworthy,
even for a superuser.

Filters by user and entity type are applied server-side (see
api_client.list_audit_logs()), not client-side -- unlike a single
ticket's own small, naturally-bounded history, this table can grow
large across months of real usage, so filtering happens on the
backend rather than fetching everything every time.

Only reachable from the Settings window, which is already
superuser-gated before it's ever opened (see settings_window.py).
"""

from PySide6.QtCore import Qt
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

from desktop import api_client, layout
from desktop.api_client import ApiError
from desktop.audit_log_entry_dialog import AuditLogEntryDialog
from desktop.formatting import format_timestamp

COLUMN_HEADERS = ["Timestamp", "User", "Action", "Entity", "Details"]

# Known entity types actually in use throughout the app -- not a real
# backend enum (entity_type is just a free string field by
# convention), but a fixed list here keeps the filter dropdown simple
# and predictable rather than dynamically inferred from whatever
# happens to already be in the log.
ENTITY_TYPES = ["ticket", "user", "customer", "device", "discount", "service", "tax_rate"]


class AuditLogTab(QWidget):
    """Filterable, read-only view of the full audit trail."""

    def __init__(self):
        """Builds the filter row and table, then loads the full (unfiltered) log."""
        super().__init__()
        self._build_ui()
        self._load_users()
        self._load_data()

    def _build_ui(self):
        """Builds the User and Entity Type filter dropdowns, status label, and table."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        filter_row = QHBoxLayout()

        self.user_filter = QComboBox()
        self.user_filter.addItem("All Users", userData=None)
        self.user_filter.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("User:"))
        filter_row.addWidget(self.user_filter)

        self.entity_type_filter = QComboBox()
        self.entity_type_filter.addItem("All Entity Types", userData=None)
        for entity_type in ENTITY_TYPES:
            self.entity_type_filter.addItem(entity_type.capitalize(), userData=entity_type)
        self.entity_type_filter.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("Entity Type:"))
        filter_row.addWidget(self.entity_type_filter)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.clicked.connect(self._load_data)
        filter_row.addWidget(refresh_button)

        filter_row.addStretch()
        outer_layout.addLayout(filter_row)

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    def _load_users(self):
        """Fills the User filter with every real user, for the "pull up one user's history" case."""
        try:
            users = api_client.list_users()
        except ApiError:
            return  # Filter still works with just "All Users" if this fails
        for user in sorted(users, key=lambda u: f"{u['first_name']} {u['last_name']}"):
            label = f"{user['first_name']} {user['last_name']}"
            self.user_filter.addItem(label, userData=user["id"])

    def _load_data(self):
        """Fetches audit log entries filtered to the current dropdown selections."""
        user_id = self.user_filter.currentData()
        entity_type = self.entity_type_filter.currentData()

        self.status_label.setText("Loading...")
        try:
            entries = api_client.list_audit_logs(user_id=user_id, entity_type=entity_type)
        except ApiError as e:
            self.status_label.setText(f"Couldn't load audit log: {e}")
            self.table.setRowCount(0)
            return

        self._render_table(entries)
        self.status_label.setText(f"Showing {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")

    def _render_table(self, entries: list[dict]):
        """
        Args:
            entries: Audit log entries to display, already filtered
                server-side.
        """
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                format_timestamp(entry.get("created_at", "")),
                entry.get("user_name") or "System",
                entry.get("action", ""),
                f"{entry.get('entity_type', '')} #{entry.get('entity_id', '')}",
                entry.get("details") or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, entry)
                self.table.setItem(row, col, item)

    def _on_row_double_clicked(self):
        """Opens the double-clicked row's full entry in a read-only popup -- the table cell itself is too cramped for a genuinely long, multi-field details message."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return
        entry = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = AuditLogEntryDialog(entry, parent=self)
        dialog.exec()
