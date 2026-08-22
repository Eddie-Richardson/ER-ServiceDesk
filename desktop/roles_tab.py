# ER-ServiceDesk/desktop/roles_tab.py

"""
Settings tab for managing roles: list, create, edit (including
permission grants), and delete.

Structurally similar to LookupTab but not built on it -- roles have a
genuinely different shape (permission checkboxes, not a plain
description field) that doesn't fit the generic lookup pattern.
"""

from PySide6.QtCore import QThread, Qt
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
from desktop.api_client import list_permissions, list_roles
from desktop.base_dialog import AppWindow
from desktop.lookup_save_worker import LookupSaveWorker
from desktop.lookup_worker import LookupDataWorker
from desktop.lock_gate import LockGate
from desktop.role_form_dialog import RoleFormDialog

COLUMN_HEADERS = ["Name", "Description", "Permissions"]


class RolesTab(AppWindow):
    """Settings tab for managing roles and their permission grants."""

    def __init__(self):
        """Builds the toolbar and table, then loads roles and permissions."""
        super().__init__()
        self.all_roles: list[dict] = []
        self.all_permissions: list[dict] = []

        self._roles_thread: QThread | None = None
        self._roles_worker: LookupDataWorker | None = None
        self._permissions_thread: QThread | None = None
        self._permissions_worker: LookupDataWorker | None = None
        self._delete_thread: QThread | None = None
        self._delete_worker: LookupSaveWorker | None = None
        self._lock_gate = LockGate(self)

        self._build_ui()
        self._load_data()

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

        toolbar = QHBoxLayout()
        new_button = QPushButton("New Role")
        new_button.setFixedHeight(layout.BUTTON_HEIGHT)
        new_button.clicked.connect(self._open_new_role_dialog)
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

        self.status_label = QLabel("Loading roles...")
        self.status_label.setObjectName("subtitle")
        outer_layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(COLUMN_HEADERS))
        self.table.setHorizontalHeaderLabels(COLUMN_HEADERS)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
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
        """Starts background fetches of both roles and permissions."""
        self.status_label.setText("Loading roles...")
        self.table.setRowCount(0)

        self._roles_thread = QThread()
        self._roles_worker = LookupDataWorker(list_roles)
        self._roles_worker.moveToThread(self._roles_thread)
        self._roles_thread.started.connect(self._roles_worker.run)
        self._roles_worker.finished.connect(self._on_roles_loaded)
        self._roles_worker.finished.connect(self._roles_thread.quit)
        self._roles_worker.finished.connect(self._roles_worker.deleteLater)
        self._roles_thread.finished.connect(self._roles_thread.deleteLater)
        self._roles_thread.start()

        self._permissions_thread = QThread()
        self._permissions_worker = LookupDataWorker(list_permissions)
        self._permissions_worker.moveToThread(self._permissions_thread)
        self._permissions_thread.started.connect(self._permissions_worker.run)
        self._permissions_worker.finished.connect(self._on_permissions_loaded)
        self._permissions_worker.finished.connect(self._permissions_thread.quit)
        self._permissions_worker.finished.connect(self._permissions_worker.deleteLater)
        self._permissions_thread.finished.connect(self._permissions_thread.deleteLater)
        self._permissions_thread.start()

    def _on_roles_loaded(self, success: bool, result):
        """
        Args:
            result: The role list on success, or the caught ApiError
                on failure.
        """
        if not success:
            self.handle_api_error(result, on_other_error=lambda message: self.status_label.setText(f"Couldn't load roles: {message}"))
            return
        self.all_roles = result
        self._render_table()

    def _on_permissions_loaded(self, success: bool, result):
        """
        Args:
            result: The permission list on success, or a
                human-readable error message on failure.
        """
        if success:
            self.all_permissions = result
            # Roles and permissions load in parallel with no guaranteed
            # order -- re-render here too, in case roles already
            # finished first and rendered permission names before this
            # data existed to resolve them against.
            self._render_table()
        # A permissions-load failure isn't fatal to viewing the roles
        # list itself -- New/Edit would just show zero permission
        # checkboxes, which is a degraded-but-safe state, not a crash.

    def _render_table(self):
        """Renders every role, including a comma-joined summary of its granted permissions."""
        permissions_by_id = {p["id"]: p["name"] for p in self.all_permissions}

        self.table.setRowCount(len(self.all_roles))
        for row, role in enumerate(self.all_roles):
            permission_names = [
                permissions_by_id.get(link["permission_id"], f"#{link['permission_id']}")
                for link in role.get("role_permissions", [])
            ]
            values = [
                role.get("name", ""),
                role.get("description") or "-",
                ", ".join(permission_names) if permission_names else "-",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                cell.setData(Qt.ItemDataRole.UserRole, role)
                self.table.setItem(row, col, cell)

        self.status_label.setText(f"{len(self.all_roles)} role(s).")

    # -----------------------------------------------------------------
    # Create / edit
    # -----------------------------------------------------------------
    def _open_new_role_dialog(self):
        """Opens the role form in create mode; refreshes the list if a role was saved."""
        dialog = RoleFormDialog(None, self.all_permissions, parent=self)
        if dialog.exec():
            self._load_data()

    def _on_row_double_clicked(self):
        """Acquires an edit lock, then opens the role form pre-filled with the double-clicked row's role."""
        role = self._selected_role()
        if role is None:
            return

        def build_dialog():
            return RoleFormDialog(role, self.all_permissions, parent=self)

        def on_closed(dialog):
            if dialog.result():
                self._load_data()

        self._lock_gate.attempt_edit("role", role["id"], build_dialog, on_closed)

    def _selected_role(self) -> dict | None:
        """
        Returns:
            The currently selected row's role dict, or None if nothing
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
        """Confirms with the admin, then deletes the currently selected role."""
        role = self._selected_role()
        if role is None:
            QMessageBox.information(self, "No Selection", "Select a role to delete first.")
            return

        confirmed = QMessageBox.question(
            self,
            "Delete Role",
            f"Delete '{role['name']}'? Any users currently holding this role will lose "
            f"the permissions it grants. This can't be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.delete_button.setEnabled(False)

        self._delete_thread = QThread()
        self._delete_worker = LookupSaveWorker("/roles/", item_id=role["id"], delete=True)
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
            result: None on success, or the caught ApiError on failure.
        """
        self.delete_button.setEnabled(True)

        if not success:
            self.handle_api_error(
                result,
                on_other_error=lambda message: QMessageBox.warning(self, "Delete Failed", message),
            )
            return

        self._load_data()
