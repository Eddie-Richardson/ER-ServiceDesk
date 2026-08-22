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
from PySide6.QtGui import QColor, QFont
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
from desktop.base_dialog import AppWindow
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.lock_gate import LockGate
from desktop.asset_form_dialog import AssetFormDialog
from desktop.inventory_worker import InventoryDataWorker
from desktop.part_form_dialog import PartFormDialog
from desktop.settings_manager import get_saved_theme
from desktop.theme import DARK, LIGHT, MONO_FONT_FAMILY, get_asset_status_color

ASSET_COLUMN_HEADERS = ["ID", "Name", "Category", "Manufacturer", "Model", "Status", "Location"]
PART_COLUMN_HEADERS = ["ID", "Name", "SKU", "Qty On Hand", "Reorder At", "Supplier", "Location"]


class InventoryWindow(AppWindow):
    """Standalone window with Assets and Parts tabs."""

    window_closed = Signal()

    def __init__(self):
        """Builds both tabs, then loads data shared by both."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Inventory")
        self.resize(820, 520)
        restore_geometry(self, "InventoryWindow")

        self._thread: QThread | None = None
        self._worker: InventoryDataWorker | None = None
        self.reference_data: dict = {}
        self.all_assets: list[dict] = []
        self.all_parts: list[dict] = []
        self.show_low_stock_only = False
        self._lock_gate = LockGate(self)

        self._build_ui()
        self._load_data()

    def closeEvent(self, event):
        save_geometry(self, "InventoryWindow")
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
            result: On success, the reference_data dict from
                InventoryDataWorker. On failure, the caught ApiError.
        """
        if not success:
            self.handle_api_error(result, on_other_error=self._show_load_error)
            return

        self.reference_data = result
        self.all_assets = result["assets"]
        self.all_parts = result["parts"]

        self._render_assets_table()
        self._render_parts_table()

    def _show_load_error(self, message: str):
        """Shows the same load error in both tabs' status labels."""
        self.assets_status_label.setText(f"Couldn't load assets: {message}")
        self.parts_status_label.setText(f"Couldn't load parts: {message}")

    # -----------------------------------------------------------------
    # Assets tab
    # -----------------------------------------------------------------
    def _render_assets_table(self):
        """Renders every loaded asset into the Assets table."""
        categories_by_id = {c["id"]: c["name"] for c in self.reference_data.get("categories", [])}
        locations_by_id = {l["id"]: l["name"] for l in self.reference_data.get("locations", [])}

        theme_name = get_saved_theme()
        mono_font = QFont(MONO_FONT_FAMILY)
        bold_font = QFont()
        bold_font.setBold(True)

        self.assets_table.setRowCount(len(self.all_assets))
        for row, asset in enumerate(self.all_assets):
            status_name = asset.get("status") or "-"
            values = [
                str(asset["id"]),
                asset.get("name", ""),
                categories_by_id.get(asset.get("category_id"), "-"),
                asset.get("manufacturer") or "-",
                asset.get("model") or "-",
                status_name,
                locations_by_id.get(asset.get("location_id"), "-"),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, asset)

                if col == 0:  # ID -- a technical identifier, not prose
                    item.setFont(mono_font)
                elif col == 5:  # Status -- color-coded so it can be scanned at a glance
                    item.setFont(bold_font)
                    item.setForeground(QColor(get_asset_status_color(status_name, theme_name)))

                self.assets_table.setItem(row, col, item)

        self.assets_status_label.setText(f"{len(self.all_assets)} asset(s).")

    def _open_new_asset_dialog(self):
        """Opens the asset form in create mode; refreshes the list if an asset was saved."""
        dialog = AssetFormDialog(self.reference_data, asset=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_asset_row_double_clicked(self):
        """Acquires an edit lock, then opens the asset form pre-filled with the double-clicked row's asset."""
        selected_items = self.assets_table.selectedItems()
        if not selected_items:
            return
        asset = selected_items[0].data(Qt.ItemDataRole.UserRole)

        def build_dialog():
            return AssetFormDialog(self.reference_data, asset=asset, parent=self)

        def on_closed(dialog):
            if dialog.result():
                self._load_data()

        self._lock_gate.attempt_edit("asset", asset["id"], build_dialog, on_closed)

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
        parts = self.all_parts
        if self.show_low_stock_only:
            parts = [p for p in parts if p["quantity_on_hand"] <= p["reorder_threshold"]]

        theme_name = get_saved_theme()
        mono_font = QFont(MONO_FONT_FAMILY)
        bold_font = QFont()
        bold_font.setBold(True)
        danger_color = DARK["danger"] if theme_name == "dark" else LIGHT["danger"]

        self.parts_table.setRowCount(len(parts))
        for row, part in enumerate(parts):
            is_low_stock = part["quantity_on_hand"] <= part["reorder_threshold"]
            values = [
                str(part["id"]),
                part.get("name", ""),
                part.get("sku") or "-",
                str(part.get("quantity_on_hand", 0)),
                str(part.get("reorder_threshold", 0)),
                part.get("supplier") or "-",
                self._format_part_locations(part),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, part)

                if col in (0, 2):  # ID, SKU -- technical identifiers, not prose
                    item.setFont(mono_font)
                elif col == 3 and is_low_stock:  # Qty On Hand -- flag when at/below reorder threshold
                    item.setFont(bold_font)
                    item.setForeground(QColor(danger_color))

                self.parts_table.setItem(row, col, item)

        suffix = " (low stock only)" if self.show_low_stock_only else ""
        self.parts_status_label.setText(f"{len(parts)} part(s){suffix}.")

    def _format_part_locations(self, part: dict) -> str:
        """
        Formats a part's location breakdown for display in the table --
        a part can be split across several locations at once, so this
        is a summary, not a single lookup the way Assets' single
        location_id was.

        Args:
            part: With its "locations" list (each a {"location_id",
                "location_name", "quantity"} dict).

        Returns:
            e.g. "Bench 1 (1), Bench 2 (1), Parts Shelf (2)", or "-" if
            the part has no stock recorded at any location yet.
        """
        entries = part.get("locations") or []
        if not entries:
            return "-"
        return ", ".join(f"{e['location_name']} ({e['quantity']})" for e in entries)

    def _open_new_part_dialog(self):
        """Opens the part form in create mode; refreshes the list if a part was saved."""
        dialog = PartFormDialog(self.reference_data, part=None, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_part_row_double_clicked(self):
        """Acquires an edit lock, then opens the part form pre-filled with the double-clicked row's part."""
        selected_items = self.parts_table.selectedItems()
        if not selected_items:
            return
        part = selected_items[0].data(Qt.ItemDataRole.UserRole)

        def build_dialog():
            return PartFormDialog(self.reference_data, part=part, parent=self)

        def on_closed(dialog):
            if dialog.result():
                self._load_data()

        self._lock_gate.attempt_edit("part", part["id"], build_dialog, on_closed)
