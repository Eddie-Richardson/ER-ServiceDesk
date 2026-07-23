# ER-ServiceDesk/desktop/dashboard_window.py

"""
Main landing window shown after a successful login.

Provides the sidebar navigation to every feature area and a live summary
of ticket counts by status on the backend. The individual feature windows
(Tickets, Inventory, Customers, Users & Roles, Settings) aren't built yet
-- their nav buttons currently show a "not built yet" notice rather than
pretending to navigate somewhere. Only Logout does real work here,
alongside the live status counts.
"""

from PySide6.QtCore import Qt, QThread
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
from desktop.tickets_window import TicketsWindow

NAV_ITEMS = ["Tickets", "Inventory", "Customers", "Users & Roles", "Settings"]


class DashboardWindow(QWidget):
    """Main landing window shown after a successful login."""

    _WINDOW_BACKED_NAV_ITEMS = {"Tickets"}  # extend as more feature windows get built

    def __init__(self):
        """
        Builds the sidebar and content area, then kicks off an initial
        load of ticket status counts.
        """
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Dashboard")
        self.resize(760, 480)

        self._thread: QThread | None = None
        self._worker: DashboardWorker | None = None
        self.logout_callback = None  # set by main.py
        self._tickets_window = None  # kept alive while open

        root_layout = QHBoxLayout()
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self._build_content_area(), stretch=1)

        self.setLayout(root_layout)
        self._load_status_counts()

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
            # Only nav items backed by a real, persistent window get the
            # checkable "lit up while open" treatment. The rest currently
            # just show a message box and nothing stays open -- making
            # those checkable would leave them permanently highlighted
            # with no way to reflect "closed" state, since nothing ever
            # actually opens.
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
        Returns the nav items this session's role should see. "Users &
        Roles" maps to backend endpoints that are superuser-only
        (/users, /roles, /permissions, etc.), so it's hidden entirely
        for regular agents rather than shown and then rejected.

        Returns:
            The subset of NAV_ITEMS this session is allowed to see.
        """
        if session.is_superuser():
            return NAV_ITEMS
        return [item for item in NAV_ITEMS if item != "Users & Roles"]

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

        title = QLabel("Ticket Overview")
        title.setObjectName("title")
        self.content_layout.addWidget(title)

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
            success: Whether the fetch succeeded.
            result: On success, a list of {"name", "color", "count"}
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

        for status in result:
            row = QPushButton(f"{status['name']}  \u2014  {status['count']}")
            row.setObjectName("secondary")
            row.setFixedHeight(layout.BUTTON_HEIGHT)
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
