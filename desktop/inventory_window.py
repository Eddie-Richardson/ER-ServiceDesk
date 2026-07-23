# ER-ServiceDesk/desktop/inventory_window.py

"""
Inventory window: Assets and Parts as two tabs sharing one data load.

Assets (serialized, one-off items like a bench tool) and Parts
(quantity-tracked consumable stock like "50x SSD 500GB") are different
backend resources, but they're presented as one coherent "Inventory"
concept to the user -- both tabs share the same Location lookup and the
same data-loading pass (InventoryDataWorker), rather than each tab
re-fetching independently.

Emits window_closed, same as TicketsWindow, so the Dashboard's nav
button can stay highlighted only while this window is genuinely open.
"""

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.asset_form_dialog import AssetFormDialog
from desktop.inventory_worker import InventoryDataWorker
from desktop.part_form_dialog import PartFormDialog

ASSET_COLUMN_HEADERS = ["ID", "Name", "Category", "Manufacturer", "Model", "Status", "Location"]
PART_COLUMN_HEADERS = ["ID", "Name", "SKU", "Qty On Hand", "Reorder At", "Supplier", "Location"]


class InventoryWindow(QWidget):
    """Standalone window with Assets and Parts tabs."""

    window_closed = Signal()

    def __init__(self):
        """Builds both tabs, then loads data shared by both."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Inventory")
        self.resize(820, 520)

        self._thread: QThread | None = None
        self._worker: InventoryDataWorker | None = None
        self.reference_data: dict = {}
        self.all_assets: list[dict] = []
        self.all_parts: list[dict] = []
        self.show_low_stock_only = False

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
        """Builds the tab widget and both tabs' contents."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )

        title = QLabel("Inventory")
        title.setObjectName("title")
        outer_layout.addWidget(title)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_assets_tab(), "Assets")
        self.tabs.addTab(self._build_parts_tab(), "Parts")
        outer_layout.addWidget(self.tabs)

        self.setLayout(outer_layout)

    def _build_assets_tab(self) -> QWidget:
        """
        Returns:
            The assembled Assets tab: toolbar, status label, and table.
        """
        tab = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.setSpacing(layout.SPACE_MD)

        toolbar = QHBoxLayout()
        new_button = QPushButton("New Asset")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_asset_dialog)
        toolbar.addWidget(new_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch()
        tab_layout.addLayout(toolbar)

        self.assets_status_label = QLabel("Loading assets...")
        self.assets_status_label.setObjectName("subtitle")
        tab_layout.addWidget(self.assets_status_label)

        self.assets_table = QTableWidget()
        self.assets_table.setColumnCount(len(ASSET_COLUMN_HEADERS))
        self.assets_table.setHorizontalHeaderLabels(ASSET_COLUMN_HEADERS)
        self.assets_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.assets_table.verticalHeader().setVisible(False)
        self.assets_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.assets_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.assets_table.doubleClicked.connect(self._on_asset_row_double_clicked)
        tab_layout.addWidget(self.assets_table)

        tab.setLayout(tab_layout)
        return tab

    def _build_parts_tab(self) -> QWidget:
        """
        Returns:
            The assembled Parts tab: toolbar (including the Low Stock
            toggle), status label, and table.
        """
        tab = QWidget()
        tab_layout = QVBoxLayout()
        tab_layout.setSpacing(layout.SPACE_MD)

        toolbar = QHBoxLayout()
        new_button = QPushButton("New Part")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_part_dialog)
        toolbar.addWidget(new_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)

        self.low_stock_button = QPushButton("Low Stock Only")
        self.low_stock_button.setObjectName("secondary")
        self.low_stock_button.setCheckable(True)
        self.low_stock_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.low_stock_button.clicked.connect(self._toggle_low_stock_filter)
        toolbar.addWidget(self.low_stock_button)
        toolbar.addStretch()
        tab_layout.addLayout(toolbar)

        self.parts_status_label = QLabel("Loading parts...")
        self.parts_status_label.setObjectName("subtitle")
        tab_layout.addWidget(self.parts_status_label)

        self.parts_table = QTableWidget()
        self.parts_table.setColumnCount(len(PART_COLUMN_HEADERS))
        self.parts_table.setHorizontalHeaderLabels(PART_COLUMN_HEADERS)
        self.parts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.parts_table.verticalHeader().setVisible(False)
        self.parts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.parts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.parts_table.doubleClicked.connect(self._on_part_row_double_clicked)
        tab_layout.addWidget(self.parts_table)

        tab.setLayout(tab_layout)
        return tab

    # -----------------------------------------------------------------
    # Data loading
    # -----------------------------------------------------------------
    def _load_data(self):
        """Starts a background fetch of assets, parts, and their reference data."""
        self.assets_status_label.setText("Loading assets...")
        self.parts_status_label.setText("Loading parts...")
        self.assets_table.setRowCount(0)
        self.parts_table.setRowCount(0)

        self._thread = QThread()
        self._worker = InventoryDataWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_data_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_data_loaded(self, success: bool, result):
        """
        Handles the background load's result: renders both tabs on
        success, or shows an error in both status labels on failure.

        Args:
            success: Whether the load succeeded.
            result: On success, the reference_data dict from
                InventoryDataWorker. On failure, a human-readable error
                message string.
        """
        if not success:
            self.assets_status_label.setText(f"Couldn't load assets: {result}")
            self.parts_status_label.setText(f"Couldn't load parts: {result}")
            return

        self.reference_data = result
        self.all_assets = result["assets"]
        self.all_parts = result["parts"]

        self._render_assets_table()
        self._render_parts_table()

    # -----------------------------------------------------------------
    # Assets tab
    # -----------------------------------------------------------------
    def _render_assets_table(self):
        """Renders every loaded asset into the Assets table."""
        categories_by_id = {c["id"]: c["name"] for c in self.reference_data.get("categories", [])}
        locations_by_id = {l["id"]: l["name"] for l in self.reference_data.get("locations", [])}

        self.assets_table.setRowCount(len(self.all_assets))
        for row, asset in enumerate(self.all_assets):
            values = [
                str(asset["id"]),
                asset.get("name", ""),
                categories_by_id.get(asset.get("category_id"), "-"),
                asset.get("manufacturer") or "-",
                asset.get("model") or "-",
                asset.get("status") or "-",
                locations_by_id.get(asset.get("location_id"), "-"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, asset)
                self.assets_table.setItem(row, col, item)

        self.assets_status_label.setText(f"{len(self.all_assets)} asset(s).")

    def _open_new_asset_dialog(self):
        """Opens the asset form in create mode; refreshes the list if an asset was saved."""
        dialog = AssetFormDialog(self.reference_data, asset=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_asset_row_double_clicked(self):
        """Opens the asset form pre-filled with the double-clicked row's asset."""
        selected_items = self.assets_table.selectedItems()
        if not selected_items:
            return
        asset = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = AssetFormDialog(self.reference_data, asset=asset, parent=self)
        if dialog.exec():
            self._load_data()

    # -----------------------------------------------------------------
    # Parts tab
    # -----------------------------------------------------------------
    def _toggle_low_stock_filter(self):
        """Flips the Low Stock filter and re-renders the Parts table."""
        self.show_low_stock_only = self.low_stock_button.isChecked()
        self._render_parts_table()

    def _render_parts_table(self):
        """
        Renders parts into the Parts table, filtered to low-stock only
        if that toggle is active. "Low stock" is computed client-side
        (quantity_on_hand <= reorder_threshold) against the already-
        fetched full parts list, rather than making a second network
        call to the backend's dedicated low-stock endpoint -- the data
        needed is already in memory from the initial load.
        """
        locations_by_id = {l["id"]: l["name"] for l in self.reference_data.get("locations", [])}

        parts = self.all_parts
        if self.show_low_stock_only:
            parts = [p for p in parts if p["quantity_on_hand"] <= p["reorder_threshold"]]

        self.parts_table.setRowCount(len(parts))
        for row, part in enumerate(parts):
            values = [
                str(part["id"]),
                part.get("name", ""),
                part.get("sku") or "-",
                str(part.get("quantity_on_hand", 0)),
                str(part.get("reorder_threshold", 0)),
                part.get("supplier") or "-",
                locations_by_id.get(part.get("location_id"), "-"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, part)
                self.parts_table.setItem(row, col, item)

        suffix = " (low stock only)" if self.show_low_stock_only else ""
        self.parts_status_label.setText(f"{len(parts)} part(s){suffix}.")

    def _open_new_part_dialog(self):
        """Opens the part form in create mode; refreshes the list if a part was saved."""
        dialog = PartFormDialog(self.reference_data, part=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_part_row_double_clicked(self):
        """Opens the part form pre-filled with the double-clicked row's part."""
        selected_items = self.parts_table.selectedItems()
        if not selected_items:
            return
        part = selected_items[0].data(Qt.ItemDataRole.UserRole)
        dialog = PartFormDialog(self.reference_data, part=part, parent=self)
        if dialog.exec():
            self._load_data()
