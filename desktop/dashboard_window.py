# ER-ServiceDesk/desktop/dashboard_window.py

"""
Main landing window shown after a successful login.

Provides the sidebar navigation to every feature area and a live summary
of ticket counts by status on the backend, with clickable status cards
that open Tickets pre-filtered.
"""

from PySide6.QtCore import QThread
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import layout, session
from desktop.dashboard_worker import DashboardWorker
from desktop.billing_window import BillingWindow
from desktop.customers_window import CustomersWindow
from desktop.settings_window import SettingsWindow
from desktop.users_roles_window import UsersRolesWindow
from desktop.inventory_window import InventoryWindow
from desktop.tickets_window import TicketsWindow
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.settings_manager import get_saved_theme, get_business_name
from desktop.theme import MONO_FONT_FAMILY, get_status_color

NAV_ITEMS = ["Tickets", "Inventory", "Customers", "Billing", "Users & Roles", "Settings"]


class DashboardWindow(QWidget):
    """Main landing window shown after a successful login."""

    _WINDOW_BACKED_NAV_ITEMS = {"Tickets", "Inventory", "Customers", "Billing", "Users & Roles", "Settings"}

    def __init__(self):
        """
        Builds the sidebar and content area, then kicks off an initial
        load of ticket status counts.
        """
        super().__init__()
        business_name = get_business_name()
        self.setWindowTitle(f"ER-ServiceDesk - {business_name} - Dashboard" if business_name else "ER-ServiceDesk - Dashboard")
        self.resize(760, 480)
        restore_geometry(self, "DashboardWindow")

        self._thread: QThread | None = None
        self._worker: DashboardWorker | None = None
        self.logout_callback = None  # set by main.py
        self._tickets_window = None  # kept alive while open
        self._inventory_window = None  # kept alive while open
        self._customers_window = None  # kept alive while open
        self._users_roles_window = None  # kept alive while open
        self._settings_window = None  # kept alive while open

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)

        self.setLayout(root_layout)
        self._load_status_counts()

    def closeEvent(self, event):
        save_geometry(self, "DashboardWindow")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # Sidebar
    # -----------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        """
        Constructs the left-hand navigation sidebar.

        Returns:
            The assembled sidebar QWidget, ready to add to the root layout.
        """
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(layout.SIDEBAR_WIDTH)

        sidebar_layout = QVBoxLayout()
        sidebar_layout.setContentsMargins(
            layout.SPACE_SM, layout.SPACE_MD, layout.SPACE_SM, layout.SPACE_MD
        )
        sidebar_layout.setSpacing(layout.SPACE_XS)

        heading = QLabel("ER-ServiceDesk")
        heading.setObjectName("title")
        heading.setContentsMargins(layout.SPACE_SM, 0, 0, layout.SPACE_MD)
        sidebar_layout.addWidget(heading)

        self._nav_buttons: dict[str, QPushButton] = {}
        for label in self._visible_nav_items():
            button = QPushButton(label)
            button.setObjectName("navButton")
            # Checkable "lit up while open" treatment only applies to
            # nav items backed by a real, persistent window -- a nav
            # item with no persistent window has no "closed" state to
            # reflect, so making it checkable would leave it
            # permanently highlighted with no way to turn off.
            button.setCheckable(label in self._WINDOW_BACKED_NAV_ITEMS)
            button.setFixedHeight(layout.NAV_BUTTON_HEIGHT)
            button.clicked.connect(lambda _checked, name=label: self._on_nav_clicked(name))
            sidebar_layout.addWidget(button)
            self._nav_buttons[label] = button

        sidebar_layout.addStretch()

        logout_button = QPushButton("Log Out")
        logout_button.setObjectName("secondary")
        logout_button.setFixedHeight(layout.BUTTON_HEIGHT)
        logout_button.clicked.connect(self._on_logout)
        sidebar_layout.addWidget(logout_button)

        sidebar.setLayout(sidebar_layout)
        return sidebar

    def _visible_nav_items(self) -> list[str]:
        """
        Returns the nav items this session's role should see.

        "Users & Roles" and "Settings" both map to superuser-only
        backend endpoints, so they're hidden entirely for everyone else
        rather than shown and then rejected. "Tickets", "Customers",
        "Inventory", and "Billing" are each gated on their matching
        permission (tickets.manage / customers.manage /
        inventory.manage / billing.manage) for the same reason --
        showing a nav item that just 403s when clicked is the wrong
        default, not just for the superuser-only windows.

        Returns:
            The subset of NAV_ITEMS this session is allowed to see.
        """
        if session.is_superuser():
            return NAV_ITEMS

        permission_gates = {
            "Tickets": "tickets.manage",
            "Customers": "customers.manage",
            "Inventory": "inventory.manage",
            "Billing": "billing.manage",
        }

        visible = []
        for item in NAV_ITEMS:
            if item in ("Users & Roles", "Settings"):
                continue  # superuser-only, never shown otherwise
            required_permission = permission_gates.get(item)
            if required_permission and not session.has_permission(required_permission):
                continue
            visible.append(item)
        return visible

    def _on_nav_clicked(self, name: str):
        """
        Handles a click on a sidebar nav button. Opens the matching
        window if it's built; otherwise shows an honest "not built yet"
        notice rather than pretending to navigate.

        Args:
            name: The clicked nav item's label, e.g. "Tickets".
        """
        if name == "Tickets":
            self._open_tickets_window()
            return

        if name == "Inventory":
            self._open_inventory_window()
            return

        if name == "Customers":
            self._open_customers_window()
            return

        if name == "Billing":
            self._open_billing_window()
            return

        if name == "Users & Roles":
            self._open_users_roles_window()
            return

        if name == "Settings":
            self._open_settings_window()
            return

        QMessageBox.information(
            self, name, f"The {name} window isn't built yet -- coming soon."
        )

    def _open_tickets_window(self, initial_status_filter: str | None = None):
        """
        Opens the Tickets window and keeps its nav button highlighted for
        exactly as long as the window is actually open -- not just "was
        clicked at some point." The button un-highlights itself via
        TicketsWindow.window_closed once the person closes the window.

        Args:
            initial_status_filter: Passed straight through to
                TicketsWindow, e.g. when opened from a Dashboard status
                card rather than the sidebar.
        """
        self._tickets_window = TicketsWindow(initial_status_filter=initial_status_filter)

        tickets_button = self._nav_buttons.get("Tickets")
        if tickets_button:
            tickets_button.setChecked(True)
            self._tickets_window.window_closed.connect(
                lambda: tickets_button.setChecked(False)
            )

        self._tickets_window.show()

    def _open_inventory_window(self):
        """
        Opens the Inventory window and keeps its nav button highlighted
        for exactly as long as the window is actually open, same pattern
        as _open_tickets_window.
        """
        self._inventory_window = InventoryWindow()

        inventory_button = self._nav_buttons.get("Inventory")
        if inventory_button:
            inventory_button.setChecked(True)
            self._inventory_window.window_closed.connect(
                lambda: inventory_button.setChecked(False)
            )

        self._inventory_window.show()

    def _open_customers_window(self):
        """
        Opens the Customers window and keeps its nav button highlighted
        for exactly as long as the window is actually open, same pattern
        as _open_tickets_window and _open_inventory_window.
        """
        self._customers_window = CustomersWindow()

        customers_button = self._nav_buttons.get("Customers")
        if customers_button:
            customers_button.setChecked(True)
            self._customers_window.window_closed.connect(
                lambda: customers_button.setChecked(False)
            )

        self._customers_window.show()

    def _open_billing_window(self):
        """
        Opens the Billing window and keeps its nav button highlighted
        for exactly as long as the window is actually open, same
        pattern as every other feature window.
        """
        self._billing_window = BillingWindow()

        billing_button = self._nav_buttons.get("Billing")
        if billing_button:
            billing_button.setChecked(True)
            self._billing_window.window_closed.connect(
                lambda: billing_button.setChecked(False)
            )

        self._billing_window.show()

    def _open_users_roles_window(self):
        """
        Opens the Users & Roles window and keeps its nav button
        highlighted for exactly as long as the window is actually open,
        same pattern as every other feature window. Only ever reachable
        by superusers -- _visible_nav_items() hides this nav item for
        everyone else, so no additional check is needed here.
        """
        self._users_roles_window = UsersRolesWindow()

        users_roles_button = self._nav_buttons.get("Users & Roles")
        if users_roles_button:
            users_roles_button.setChecked(True)
            self._users_roles_window.window_closed.connect(
                lambda: users_roles_button.setChecked(False)
            )

        self._users_roles_window.show()

    def _open_settings_window(self):
        """
        Opens the Settings window and keeps its nav button highlighted
        for exactly as long as the window is actually open, same
        pattern as every other feature window. Only ever reachable by
        superusers -- _visible_nav_items() hides this nav item for
        everyone else, so no additional check is needed here.
        """
        self._settings_window = SettingsWindow()

        settings_button = self._nav_buttons.get("Settings")
        if settings_button:
            settings_button.setChecked(True)
            self._settings_window.window_closed.connect(
                lambda: settings_button.setChecked(False)
            )

        self._settings_window.show()

    def _on_logout(self):
        """
        Clears the session, hands off to whatever the caller wired up as
        the post-logout action (typically opening a fresh Login window),
        then closes this window.

        Closing self here is deliberate, not incidental: on a shared shop
        machine, leaving a logged-out user's Dashboard rendered on screen
        -- ticket data and all -- after they've logged out is a real
        exposure. The next person at the machine should see a login
        screen, not a stale authenticated view.
        """
        session.clear()
        if self.logout_callback:
            self.logout_callback()
        self.close()

    # -----------------------------------------------------------------
    # Main content: ticket status counts
    # -----------------------------------------------------------------
    def _build_content_area(self) -> QWidget:
        """
        Constructs the main content area, including the ticket-status
        counts region that _load_status_counts() populates.

        Returns:
            The assembled content QWidget, ready to add to the root layout.
        """
        content = QWidget()

        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        self.content_layout.setSpacing(layout.SPACE_MD)

        header_row = QHBoxLayout()
        title = QLabel("Ticket Overview")
        title.setObjectName("title")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_status_counts)
        header_row.addWidget(refresh_button)

        self.content_layout.addLayout(header_row)

        self.status_area_layout = QVBoxLayout()
        self.status_area_layout.setSpacing(layout.SPACE_SM)
        self.content_layout.addLayout(self.status_area_layout)
        self.content_layout.addStretch()

        content.setLayout(self.content_layout)
        return content

    def _clear_status_area(self):
        """Removes every widget currently in the status counts area."""
        while self.status_area_layout.count():
            item = self.status_area_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _load_status_counts(self):
        """
        Starts a background fetch of ticket status counts. Shows a
        loading label immediately, then hands off to _on_counts_loaded
        once the worker thread finishes.
        """
        self._clear_status_area()
        loading_label = QLabel("Loading ticket counts...")
        loading_label.setObjectName("subtitle")
        self.status_area_layout.addWidget(loading_label)

        self._thread = QThread()
        self._worker = DashboardWorker()
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_counts_loaded)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_counts_loaded(self, success: bool, result):
        """
        Handles the result of the background status-count fetch. Renders
        one row per status on success, an error + Retry button on
        failure, or an empty-state message if no statuses exist yet.

        Args:
            result: On success, a list of {"name", "count"}
                dicts. On failure, a human-readable error message string.
        """
        self._clear_status_area()

        if not success:
            error_label = QLabel(f"Couldn't load ticket counts: {result}")
            error_label.setObjectName("subtitle")
            error_label.setWordWrap(True)
            self.status_area_layout.addWidget(error_label)

            retry_button = QPushButton("Retry")
            retry_button.setObjectName("secondary")
            retry_button.clicked.connect(self._load_status_counts)
            self.status_area_layout.addWidget(retry_button)
            return

        if not result:
            empty_label = QLabel("No ticket statuses have been configured yet.")
            empty_label.setObjectName("subtitle")
            self.status_area_layout.addWidget(empty_label)
            return

        theme_name = get_saved_theme()
        mono_font = QFont(MONO_FONT_FAMILY)
        mono_font.setBold(True)

        for status in result:
            row = QPushButton(f"{status['name']}  \u2014  {status['count']}")
            row.setObjectName("secondary")
            row.setFixedHeight(layout.BUTTON_HEIGHT)
            row.setFont(mono_font)
            row.setStyleSheet(f"color: {get_status_color(status['name'], theme_name)};")
            row.clicked.connect(
                lambda _checked, name=status["name"]: self._on_status_clicked(name)
            )
            self.status_area_layout.addWidget(row)

    def _on_status_clicked(self, status_name: str):
        """
        Opens the Tickets window pre-filtered to just this status, via
        the same path as clicking the Tickets nav button -- so the nav
        button highlights correctly regardless of which entry point was
        used to open the window.

        Args:
            status_name: The clicked status's name, e.g. "Open".
        """
        self._open_tickets_window(initial_status_filter=status_name)