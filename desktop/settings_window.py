# ER-ServiceDesk/desktop/settings_window.py

"""
Settings window: admin-only management of every lookup table used
throughout the app, plus Roles.

Eight tabs: five identically-shaped lookup tables (Locations, Asset
Categories, Ticket Categories, Ticket Statuses, Ticket Types) sharing
one reusable LookupTab widget, Roles (a genuinely different shape --
permission checkboxes, not a plain description field -- so it gets
its own RolesTab rather than being forced into the generic pattern),
plus mode-specific tabs: Local installs get Migrate to Server and
Database Backup (both need a local database to operate on, so neither
applies to Client), and Client installs get Server Resources (needs an
ongoing connection to a Server, which only Client actually has -- Local
has no reason to remotely resize itself, and Server never opens this
window in the first place, since no exe is ever installed there).

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
from desktop.database_backup_tab import DatabaseBackupTab
from desktop.lookup_tab import LookupTab
from desktop.migrate_to_server_tab import MigrateToServerTab
from desktop.roles_tab import RolesTab
from desktop.server_resources_tab import ServerResourcesTab
from desktop.settings_manager import get_install_mode
from desktop.window_geometry import restore_geometry, save_geometry


class SettingsWindow(QWidget):
    """Standalone window managing every lookup table, Roles, and (for Local installs) Migrate to Server and Database Backup."""

    window_closed = Signal()

    def __init__(self):
        """Builds every tab."""
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
            LookupTab("Location", list_locations, "/inventory/locations/", "location"),
            "Locations",
        )
        tabs.addTab(
            LookupTab("Asset Category", list_asset_categories, "/inventory/asset_categories/", "asset_category"),
            "Asset Categories",
        )
        tabs.addTab(
            LookupTab("Ticket Category", list_ticket_categories, "/ticket_categories/", "ticket_category"),
            "Ticket Categories",
        )
        tabs.addTab(
            LookupTab("Ticket Status", list_ticket_statuses, "/ticket_statuses/", "ticket_status"),
            "Ticket Statuses",
        )
        tabs.addTab(
            LookupTab("Ticket Type", list_ticket_types, "/ticket_types/", "ticket_type"),
            "Ticket Types",
        )
        tabs.addTab(RolesTab(), "Roles")

        # Migrate to Server and Database Backup both only make sense
        # for Local mode -- Client is already pointed at a server (for
        # Migrate to Server) and has no local database at all (for
        # either tab). Server mode never opens this window in the
        # first place (no exe is ever installed there), so no separate
        # check is needed for that case.
        if get_install_mode() == "local":
            tabs.addTab(MigrateToServerTab(), "Migrate to Server")
            tabs.addTab(DatabaseBackupTab(), "Database Backup")

        # Server Resources only makes sense for Client mode -- it's
        # the one install mode with an ongoing network connection to a
        # Server to send these commands over at all (the same reason
        # Migrate to Server is Local-only: each direction only has one
        # mode that's actually positioned to initiate it).
        if get_install_mode() == "client":
            tabs.addTab(ServerResourcesTab(), "Server Resources")

        outer_layout.addWidget(tabs)
        self.setLayout(outer_layout)
