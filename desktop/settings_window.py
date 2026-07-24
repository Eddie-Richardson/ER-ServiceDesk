# ER-ServiceDesk/desktop/settings_window.py

"""
Settings window: admin-only management of every lookup table used
throughout the app, plus Roles.

Six tabs: five identically-shaped lookup tables (Locations, Asset
Categories, Ticket Categories, Ticket Statuses, Ticket Types) sharing
one reusable LookupTab widget, plus Roles (a genuinely different shape
-- permission checkboxes, not a plain description field -- so it gets
its own RolesTab rather than being forced into the generic pattern).

Superuser-only -- gated by the Dashboard before this window is ever
opened, same as Users & Roles.

Emits window_closed, same as every other feature window, so the
Dashboard's nav button only stays highlighted while this window is
genuinely open.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from desktop.api_client import (
    list_asset_categories,
    list_locations,
    list_ticket_categories,
    list_ticket_statuses,
    list_ticket_types,
)
from desktop.lookup_tab import LookupTab
from desktop.roles_tab import RolesTab
from desktop.window_geometry import restore_geometry, save_geometry


class SettingsWindow(QWidget):
    """Standalone window managing every lookup table plus Roles."""

    window_closed = Signal()

    def __init__(self):
        """Builds all six tabs."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Settings")
        self.resize(760, 560)
        restore_geometry(self, "SettingsWindow")

        self._build_ui()

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "SettingsWindow")
        super().closeEvent(event)
        self.window_closed.emit()

    def _build_ui(self):
        """Builds the tab widget and every tab's contents."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(
            LookupTab("Location", list_locations, "/inventory/locations/"),
            "Locations",
        )
        tabs.addTab(
            LookupTab("Asset Category", list_asset_categories, "/inventory/asset_categories/"),
            "Asset Categories",
        )
        tabs.addTab(
            LookupTab("Ticket Category", list_ticket_categories, "/ticket_categories/"),
            "Ticket Categories",
        )
        tabs.addTab(
            LookupTab("Ticket Status", list_ticket_statuses, "/ticket_statuses/"),
            "Ticket Statuses",
        )
        tabs.addTab(
            LookupTab("Ticket Type", list_ticket_types, "/ticket_types/"),
            "Ticket Types",
        )
        tabs.addTab(RolesTab(), "Roles")

        outer_layout.addWidget(tabs)
        self.setLayout(outer_layout)
