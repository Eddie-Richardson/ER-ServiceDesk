# ER-ServiceDesk/desktop/background_jobs_tab.py

"""
Settings tab for browsing and filtering background job run history --
inbound email polling, automatic customer archiving, and part-status
customer notifications.

Read-only, matching the backend (see app/routes/background_jobs.py) --
job history a user could edit through this tab wouldn't be trustworthy
(a failed job could be silently marked "completed", hiding a real
problem).

Filters by job type and status are applied server-side (see
api_client.list_background_jobs()), not client-side, same reasoning as
the Audit Log tab -- this table can grow large across months of real
usage.

Only reachable from the Settings window, which is already
superuser-gated before it's ever opened (see settings_window.py).
"""

from datetime import datetime

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

COLUMN_HEADERS = ["Started", "Job Type", "Status", "Payload / Error"]

# Every real background job type in this app -- not a backend enum
# (job_type is a free string field by convention), matching the same
# reasoning as ENTITY_TYPES in audit_log_tab.py.
JOB_TYPES = ["poll_inbound_email", "archive_inactive_customers", "notify_customer_of_part_status_change"]
STATUSES = ["running", "completed", "failed"]


def _format_timestamp(iso_string: str) -> str:
    """Formats an ISO datetime string for display, e.g. 'Aug 8, 2026 3:45 PM'. Returns the raw string unchanged if it can't be parsed."""
    try:
        dt = datetime.fromisoformat(iso_string)
        return dt.strftime("%b %-d, %Y %-I:%M %p")
    except (ValueError, TypeError):
        return iso_string or ""


class BackgroundJobsTab(QWidget):
    """Filterable, read-only view of background job run history."""

    def __init__(self):
        """Builds the filter row and table, then loads the full (unfiltered) history."""
        super().__init__()
        self._build_ui()
        self._load_data()

    def _build_ui(self):
        """Builds the Job Type and Status filter dropdowns, status label, and table."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        filter_row = QHBoxLayout()

        self.job_type_filter = QComboBox()
        self.job_type_filter.addItem("All Job Types", userData=None)
        for job_type in JOB_TYPES:
            self.job_type_filter.addItem(job_type, userData=job_type)
        self.job_type_filter.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("Job Type:"))
        filter_row.addWidget(self.job_type_filter)

        self.status_filter = QComboBox()
        self.status_filter.addItem("All Statuses", userData=None)
        for status in STATUSES:
            self.status_filter.addItem(status.capitalize(), userData=status)
        self.status_filter.currentIndexChanged.connect(self._load_data)
        filter_row.addWidget(QLabel("Status:"))
        filter_row.addWidget(self.status_filter)

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
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    def _load_data(self):
        """Fetches job history filtered to the current dropdown selections."""
        job_type = self.job_type_filter.currentData()
        status = self.status_filter.currentData()

        self.status_label.setText("Loading...")
        try:
            entries = api_client.list_background_jobs(job_type=job_type, status=status)
        except ApiError as e:
            self.status_label.setText(f"Couldn't load background jobs: {e}")
            self.table.setRowCount(0)
            return

        self._render_table(entries)
        self.status_label.setText(f"Showing {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}.")

    def _render_table(self, entries: list[dict]):
        """
        Args:
            entries: Background job entries to display, already
                filtered server-side.
        """
        self.table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            values = [
                _format_timestamp(entry.get("created_at", "")),
                entry.get("job_type", ""),
                entry.get("status", ""),
                entry.get("payload") or "",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, entry)
                self.table.setItem(row, col, item)
