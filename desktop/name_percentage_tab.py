# ER-ServiceDesk/desktop/name_percentage_tab.py

"""
Generic tab for managing a name + percentage + active catalog table --
shared by Discounts and Tax Rates, parameterized the same way
LookupTab is for name/description tables.
"""

from typing import Callable

from PySide6.QtCore import QThread, Qt, Signal
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
from desktop.name_percentage_dialog import NamePercentageDialog
from desktop.lock_gate import LockGate
from desktop.lookup_save_worker import LookupSaveWorker
from desktop.lookup_worker import LookupDataWorker

COLUMN_HEADERS = ["Name", "Percentage", "Active"]


class NamePercentageTab(QWidget):
    """A single Settings tab managing one name/percentage/is_active catalog table."""

    data_changed = Signal()

    def __init__(self, display_name: str, list_func: Callable[[], list[dict]], endpoint: str, entity_type: str):
        """
        Args:
            display_name: Shown in headings and dialogs, e.g. "Discount".
            list_func: The api_client function to call to load items,
                e.g. list_discounts.
            endpoint: The resource path for create/update/delete, e.g.
                "/discounts/".
            entity_type: Short identifier used for the check-out edit
                lock, e.g. "discount", "tax_rate".
        """
        super().__init__()
        self.display_name = display_name
        self.list_func = list_func
        self.endpoint = endpoint
        self.entity_type = entity_type
        self.all_items: list[dict] = []

        self._thread: QThread | None = None
        self._worker: LookupDataWorker | None = None
        self._delete_thread: QThread | None = None
        self._delete_worker: LookupSaveWorker | None = None
        self._lock_gate = LockGate(self)

        self._build_ui()
        self._load_data()

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
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self._on_row_double_clicked)
        outer_layout.addWidget(self.table)

        self.setLayout(outer_layout)

    def _load_data(self):
        """Starts a background fetch of every item in this catalog."""
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
            values = [
                item.get("name", ""),
                f"{item.get('percentage', 0)}%",
                "Yes" if item.get("is_active", True) else "No",
            ]
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
        dialog = NamePercentageDialog(self.display_name, self.endpoint, item=None, parent=self)
        if dialog.exec():
            self._load_data()
            self.data_changed.emit()

    def _on_row_double_clicked(self):
        """Acquires an edit lock, then opens the item form pre-filled with the double-clicked row's item."""
        item = self._selected_item()
        if item is None:
            return

        def build_dialog():
            return NamePercentageDialog(self.display_name, self.endpoint, item=item, parent=self)

        def on_closed(dialog):
            if dialog.result():
                self._load_data()
                self.data_changed.emit()

        self._lock_gate.attempt_edit(self.entity_type, item["id"], build_dialog, on_closed)

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
            f"Delete '{item['name']}'? This won't affect any existing quotes/invoices that used it -- they keep their own record of the name and amount. This can't be undone.",
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
            result: None on success, or a human-readable error message
                on failure.
        """
        self.delete_button.setEnabled(True)

        if not success:
            QMessageBox.warning(self, "Delete Failed", str(result))
            return

        self._load_data()
        self.data_changed.emit()
