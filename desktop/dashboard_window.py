# ER-ServiceDesk/desktop/dashboard_window.py
# Dashboard window: nav sidebar + live ticket status counts.
#
# The individual feature windows (Tickets, Inventory, Customers, Users &
# Roles, Settings) aren't built yet -- their nav buttons currently show a
# "not built yet" notice rather than pretending to navigate somewhere.
# Only Logout does real work here, alongside the live status counts.

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

NAV_ITEMS = ["Tickets", "Inventory", "Customers", "Users & Roles", "Settings"]


class DashboardWindow(QWidget):
    """Main landing window shown after a successful login."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Dashboard")
        self.resize(760, 480)

        self._thread: QThread | None = None
        self._worker: DashboardWorker | None = None
        self.logout_callback = None  # set by main.py

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

        for label in self._visible_nav_items():
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(True)
            button.setFixedHeight(layout.NAV_BUTTON_HEIGHT)
            button.clicked.connect(lambda _checked, name=label: self._on_nav_clicked(name))
            sidebar_layout.addWidget(button)

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
        """
        if session.is_superuser():
            return NAV_ITEMS
        return [item for item in NAV_ITEMS if item != "Users & Roles"]

    def _on_nav_clicked(self, name: str):
        QMessageBox.information(
            self, name, f"The {name} window isn't built yet -- coming soon."
        )

    def _on_logout(self):
        session.clear()
        if self.logout_callback:
            self.logout_callback()

    # -----------------------------------------------------------------
    # Main content: ticket status counts
    # -----------------------------------------------------------------
    def _build_content_area(self) -> QWidget:
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
        while self.status_area_layout.count():
            item = self.status_area_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _load_status_counts(self):
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
        QMessageBox.information(
            self,
            status_name,
            f"Filtering tickets by '{status_name}' isn't built yet -- "
            f"that'll open the Tickets window once it exists.",
        )
