# ER-ServiceDesk/desktop/settings_window.py

"""
Settings window: admin-only management of every lookup table used
throughout the app, plus Roles and every other admin-only screen.

Locations, Asset Categories, Ticket Categories, and Ticket Statuses
share one reusable LookupTab widget (identically shaped: name +
optional description). Discounts and Tax Rates share a different
reusable widget, NamePercentageTab (name + percentage). Ticket Types &
Stages and Roles each have a genuinely different shape (an allow-list
matrix, and permission checkboxes respectively), so each gets its own
dedicated tab rather than being forced into either shared widget.

Two tabs are mode-specific: Local installs get Migrate to Server and
Database Backup (both need a local database to operate on, so neither
applies to Client), and Client installs get Server Resources and
Server Backup (both need an ongoing connection to a Server, which only
Client actually has -- Local has no reason to remotely resize or back
up itself, and Server never opens this window in the first place,
since no exe is ever installed there).

Superuser-only -- gated by the Dashboard before this window is ever
opened, same as Users & Roles.

Emits window_closed, same as every other feature window, so the
Dashboard's nav button only stays highlighted while this window is
genuinely open.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout

from desktop.api_client import (
    list_asset_categories,
    list_discounts,
    list_tax_rates,
    list_ticket_categories,
    list_ticket_statuses,
)
from desktop.audit_log_tab import AuditLogTab
from desktop.background_jobs_tab import BackgroundJobsTab
from desktop.base_dialog import AppWindow
from desktop.database_backup_tab import DatabaseBackupTab
from desktop.locations_tab import LocationsTab
from desktop.lookup_tab import LookupTab
from desktop.message_templates_tab import MessageTemplatesTab
from desktop.migrate_to_server_tab import MigrateToServerTab
from desktop.name_percentage_tab import NamePercentageTab
from desktop.roles_tab import RolesTab
from desktop.server_backup_tab import ServerBackupTab
from desktop.server_resources_tab import ServerResourcesTab
from desktop.services_tab import ServicesTab
from desktop.settings_manager import get_install_mode
from desktop.business_info_tab import BusinessInfoTab
from desktop.system_settings_tab import SystemSettingsTab
from desktop.ticket_types_stages_tab import TicketTypesStagesTab
from desktop.window_geometry import restore_geometry, save_geometry


class SettingsWindow(AppWindow):
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
        save_geometry(self, "SettingsWindow")
        super().closeEvent(event)
        self.window_closed.emit()

    def _build_ui(self):
        """Builds the tab widget and every tab's contents."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)

        tabs = QTabWidget()
        tabs.addTab(LocationsTab(), "Locations")
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
        tabs.addTab(TicketTypesStagesTab(), "Ticket Types & Stages")
        tabs.addTab(RolesTab(), "Roles")
        tabs.addTab(BusinessInfoTab(), "Business Info")
        tabs.addTab(SystemSettingsTab(), "System Settings")
        tabs.addTab(AuditLogTab(), "Audit Log")
        tabs.addTab(BackgroundJobsTab(), "Background Jobs")
        tabs.addTab(MessageTemplatesTab(), "Notes Templates")
        tabs.addTab(ServicesTab(), "Services")
        tabs.addTab(NamePercentageTab("Discount", list_discounts, "/discounts/", "discount"), "Discounts")
        tabs.addTab(NamePercentageTab("Tax Rate", list_tax_rates, "/tax_rates/", "tax_rate"), "Tax Rates")

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
            tabs.addTab(ServerBackupTab(), "Server Backup")

        outer_layout.addWidget(tabs)
        self.setLayout(outer_layout)
