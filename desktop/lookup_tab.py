# ER-ServiceDesk/desktop/lookup_tab.py

"""
Generic tab for managing a simple name/description lookup table -- one
widget class shared by every lookup-table tab in Settings (Locations,
Asset Categories, Ticket Categories, Ticket Statuses, Ticket Types),
parameterized by display name, the list_* function to load with, and
the endpoint path to save/delete against.

Delete relies on the backend's own foreign-key constraints to reject
removing an item still referenced elsewhere (e.g. a Location assigned
to existing tickets) -- surfaced through the same error-message path
as everything else, rather than the desktop app trying to pre-check
every table that might reference a given lookup item.
"""

from typing import Callable

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.lookup_item_dialog import LookupItemDialog
from desktop.lookup_save_worker import LookupSaveWorker
from desktop.lookup_worker import LookupDataWorker

COLUMN_HEADERS = ["Name", "Description"]


class LookupTab(QWidget):
    """A single Settings tab managing one simple name/description lookup table."""

    def __init__(self, display_name: str, list_func: Callable[[], list[dict]], endpoint: str):
        """
        Args:
            display_name: Shown in headings and dialogs, e.g. "Location".
                Pluralized with a trailing "s" for the tab's own title.
            list_func: The api_client function to call to load items,
                e.g. list_locations.
            endpoint: The resource path for create/update/delete, e.g.
                "/inventory/locations/".
        """
        super().__init__()
        self.display_name = display_name
        self.list_func = list_func
        self.endpoint = endpoint
        self.all_items: list[dict] = []

        self._thread: QThread | None = None
        self._worker: LookupDataWorker | None = None
        self._delete_thread: QThread | None = None
        self._delete_worker: LookupSaveWorker | None = None

        self._build_ui()
        self._load_data()

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds the toolbar, status label, and table."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_MD)

        toolbar = QHBoxLayout()
        new_button = QPushButton(f"New {self.display_name}")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_item_dialog)
        toolbar.addWidget(new_button)

        self.delete_button = QPushButton("Delete Selected")
        self.delete_button.setObjectName("secondary")
        self.delete_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.delete_button.clicked.connect(self._attempt_delete_selected)
        toolbar.addWidget(self.delete_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch()
        outer_layout.addLayout(toolbar)

        self.status_label = QLabel("Loading...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
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
        """Starts a background fetch of every item in this lookup table."""
        self.status_label.setText("Loading...")
        self.table.setRowCount(0)

        self._thread = QThread()
        self._worker = LookupDataWorker(self.list_func)
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
            result: The list of items on success, or a human-readable
                error message on failure.
        """
        if not success:
            self.status_label.setText(f"Couldn't load {self.display_name.lower()}s: {result}")
            return

        self.all_items = result
        self._render_table()

    def _render_table(self):
        """Renders every item into the table."""
        self.table.setRowCount(len(self.all_items))
        for row, item in enumerate(self.all_items):
            values = [item.get("name", ""), item.get("description") or "-"]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, item)
                self.table.setItem(row, col, cell)

        self.status_label.setText(f"{len(self.all_items)} {self.display_name.lower()}(s).")

    # -----------------------------------------------------------------
    # Create / edit
    # -----------------------------------------------------------------
    def _open_new_item_dialog(self):
        """Opens the item form in create mode; refreshes the list if an item was saved."""
        dialog = LookupItemDialog(self.display_name, self.endpoint, item=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Opens the item form pre-filled with the double-clicked row's item."""
        item = self._selected_item()
        if item is None:
            return
        dialog = LookupItemDialog(self.display_name, self.endpoint, item=item, parent=self)
        if dialog.exec():
            self._load_data()

    def _selected_item(self) -> dict | None:
        """
        Returns:
            The currently selected row's item dict, or None if nothing
            is selected.
        """
        selected_items = self.table.selectedItems()
        if not selected_items:
            return None
        return selected_items[0].data(Qt.ItemDataRole.UserRole)

    # -----------------------------------------------------------------
    # Delete
    # -----------------------------------------------------------------
    def _attempt_delete_selected(self):
        """Confirms with the admin, then deletes the currently selected item."""
        item = self._selected_item()
        if item is None:
            QMessageBox.information(self, "No Selection", f"Select a {self.display_name.lower()} to delete first.")
            return

        confirmed = QMessageBox.question(
            self,
            f"Delete {self.display_name}",
            f"Delete '{item['name']}'? This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)

        self._delete_thread = QThread()
        self._delete_worker = LookupSaveWorker(self.endpoint, item_id=item["id"], delete=True)
        self._delete_worker.moveToThread(self._delete_thread)

        self._delete_thread.started.connect(self._delete_worker.run)
        self._delete_worker.finished.connect(self._on_delete_finished)
        self._delete_worker.finished.connect(self._delete_thread.quit)
        self._delete_worker.finished.connect(self._delete_worker.deleteLater)
        self._delete_thread.finished.connect(self._delete_thread.deleteLater)

        self._delete_thread.start()

    def _on_delete_finished(self, success: bool, result):
        """
        Args:
            success: Whether the delete succeeded.
            result: None on success, or a human-readable error message
                on failure (e.g. the item is still referenced elsewhere).
        """
        self.delete_button.setEnabled(True)

        if not success:
            QMessageBox.warning(self, "Delete Failed", str(result))
            return

        self._load_data()
