# ER-ServiceDesk/desktop/users_roles_window.py

"""
Users & Roles window: list of staff accounts, with create/edit and
per-user role assignment.

Superuser-only -- gated by the Dashboard before this window is ever
opened, so no additional in-window permission filtering is needed here.

Shows each user's assigned roles as a comma-joined summary column,
computed from the full user_roles link list filtered by user_id (the
backend has no per-user filtered endpoint for this join table).

Emits window_closed, same as every other feature window, so the
Dashboard's nav button only stays highlighted while this window is
genuinely open.
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
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.base_dialog import AppWindow
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.lock_gate import LockGate
from desktop.user_form_dialog import UserFormDialog
from desktop.users_roles_worker import UsersRolesDataWorker
from desktop.settings_manager import get_saved_theme
from desktop.theme import DARK, LIGHT, MONO_FONT_FAMILY

COLUMN_HEADERS = ["Name", "Email", "Active", "Superuser", "Roles"]


class UsersRolesWindow(AppWindow):
    """Standalone window listing all users, with create, edit, and role assignment."""

    window_closed = Signal()

    def __init__(self):
        """Builds the toolbar and table, then loads data."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Users & Roles")
        self.resize(760, 520)
        restore_geometry(self, "UsersRolesWindow")

        self._thread: QThread | None = None
        self._worker: UsersRolesDataWorker | None = None
        self.all_users: list[dict] = []
        self.roles: list[dict] = []
        self.user_roles: list[dict] = []
        self._lock_gate = LockGate(self)

        self._build_ui()
        self._load_data()

    def closeEvent(self, event):
        save_geometry(self, "UsersRolesWindow")
        super().closeEvent(event)
        self.window_closed.emit()

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

        title = QLabel("Users & Roles")
        title.setObjectName("title")
        outer_layout.addWidget(title)

        toolbar = QHBoxLayout()
        new_button = QPushButton("New User")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_user_dialog)
        toolbar.addWidget(new_button)

        refresh_button = QPushButton("Refresh")
        refresh_button.setObjectName("secondary")
        refresh_button.setFixedHeight(layout.BUTTON_HEIGHT)
        refresh_button.clicked.connect(self._load_data)
        toolbar.addWidget(refresh_button)
        toolbar.addStretch()
        outer_layout.addLayout(toolbar)

        self.status_label = QLabel("Loading users...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
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
        """Starts a background fetch of users, roles, and user-role assignments."""
        self.status_label.setText("Loading users...")
        self.table.setRowCount(0)

        self._thread = QThread()
        self._worker = UsersRolesDataWorker()
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
            result: On success, the data dict from UsersRolesDataWorker.
                On failure, the caught ApiError.
        """
        if not success:
            self.handle_api_error(result, on_other_error=lambda message: self.status_label.setText(f"Couldn't load users: {message}"))
            return

        self.all_users = result["users"]
        self.roles = result["roles"]
        self.user_roles = result["user_roles"]
        self._render_table()

    # -----------------------------------------------------------------
    # Table rendering
    # -----------------------------------------------------------------
    def _render_table(self):
        """Renders every user, including a comma-joined summary of their assigned roles."""
        roles_by_id = {r["id"]: r["name"] for r in self.roles}

        theme_name = get_saved_theme()
        palette = DARK if theme_name == "dark" else LIGHT
        mono_font = QFont(MONO_FONT_FAMILY)
        bold_font = QFont()
        bold_font.setBold(True)

        self.table.setRowCount(len(self.all_users))
        for row, user in enumerate(self.all_users):
            role_names = [
                roles_by_id.get(link["role_id"], "?").replace("_", " ").title()
                for link in self.user_roles
                if link["user_id"] == user["id"]
            ]

            is_active = bool(user.get("is_active"))
            is_superuser = bool(user.get("is_superuser"))

            values = [
                f"{user['first_name']} {user['last_name']}",
                user.get("email", ""),
                "Yes" if is_active else "No",
                "Yes" if is_superuser else "No",
                ", ".join(role_names) if role_names else "-",
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, user)

                if col in (1, 4):  # Email, Roles -- technical strings, not prose
                    item.setFont(mono_font)
                elif col == 2 and is_active:  # Active -- worth a positive signal when true
                    item.setFont(bold_font)
                    item.setForeground(QColor(palette["success"]))
                elif col == 3 and is_superuser:  # Superuser -- a privileged flag, worth standing out
                    item.setFont(bold_font)
                    item.setForeground(QColor(palette["accent"]))

                self.table.setItem(row, col, item)

        self.status_label.setText(f"{len(self.all_users)} user(s).")

    # -----------------------------------------------------------------
    # Create / edit
    # -----------------------------------------------------------------
    def _open_new_user_dialog(self):
        """Opens the user form in create mode; refreshes the list if a user was saved."""
        dialog = UserFormDialog(None, self.roles, self.user_roles, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Acquires an edit lock, then opens the user form pre-filled with the double-clicked row's user."""
        selected_items = self.table.selectedItems()
        if not selected_items:
            return

        user = selected_items[0].data(Qt.ItemDataRole.UserRole)

        def build_dialog():
            return UserFormDialog(user, self.roles, self.user_roles, parent=self)

        def on_closed(dialog):
            if dialog.result():
                self._load_data()

        self._lock_gate.attempt_edit("user", user["id"], build_dialog, on_closed)
