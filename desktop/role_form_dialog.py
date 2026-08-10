# ER-ServiceDesk/desktop/role_form_dialog.py

"""
Dialog for creating a new role or editing an existing one.

Permissions are a small, fixed set (hardcoded into backend route
enforcement -- see api_client.list_permissions()'s docstring for why
they're not creatable here), shown as checkboxes since a role can grant
several at once. Mirrors UserFormDialog's role-checkbox pattern one
level up: there, checkboxes pick which roles a user holds; here, they
pick which permissions a role grants.

A role's current grants come pre-embedded in its own record
(role["role_permissions"]) rather than needing a separate fetch-and-
filter the way UserRole assignments did for UserFormDialog -- the
backend's Role schema nests this directly.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from desktop import layout
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.role_save_worker import RoleSaveWorker


class RoleFormDialog(QDialog):
    """
    Modal dialog for creating or editing a role.

    Pass `role=None` to create a new role, or an existing role dict to
    edit one. On a successful save, the dialog closes itself and the
    saved role record is available via `self.saved_role`.
    """

    def __init__(self, role: dict | None, permissions: list[dict], parent=None):
        """
        Args:
            role: An existing role dict to edit, or None to create a
                new one.
            permissions: Every permission in the system, for the
                checkbox list.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.role = role
        self.permissions = permissions
        self.saved_role: dict | None = None

        self.current_links = role.get("role_permissions", []) if role else []

        self._thread: QThread | None = None
        self._worker: RoleSaveWorker | None = None

        self.setWindowTitle("Edit Role" if role else "New Role")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "RoleFormDialog")

        self._build_ui()
        if role:
            self._prefill_from_role(role)

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "RoleFormDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds Name, Description, and one checkbox per permission."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Name (required)")
        self.name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.description_input = QTextEdit()
        self.description_input.setPlaceholderText("Description (optional)")
        self.description_input.setFixedHeight(60)

        self.permission_checkboxes: dict[int, QPushButton] = {}

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save Role")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        for label_text, widget in [
            ("Name", self.name_input),
            ("Description", self.description_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        permissions_label = QLabel("Permissions")
        permissions_label.setObjectName("subtitle")
        outer_layout.addWidget(permissions_label)
        for permission in self.permissions:
            checkbox = QCheckBox(permission["name"])
            self.permission_checkboxes[permission["id"]] = checkbox
            outer_layout.addWidget(checkbox)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)
        self.name_input.setFocus()

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_role(self, role: dict):
        """
        Args:
            role: The role dict being edited.
        """
        self.name_input.setText(role.get("name", ""))
        self.description_input.setPlainText(role.get("description") or "")

        granted_permission_ids = {link["permission_id"] for link in self.current_links}
        for permission_id, checkbox in self.permission_checkboxes.items():
            checkbox.setChecked(permission_id in granted_permission_ids)

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        name = self.name_input.text().strip()
        if not name:
            self._show_error("Enter a name.")
            return

        payload = {
            "name": name,
            "description": self.description_input.toPlainText().strip() or None,
        }

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        desired_permission_ids = {
            pid for pid, checkbox in self.permission_checkboxes.items() if checkbox.isChecked()
        }
        role_id = self.role["id"] if self.role else None

        self._thread = QThread()
        self._worker = RoleSaveWorker(payload, desired_permission_ids, role_id, self.current_links)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            success: Whether the save succeeded.
            result: The saved role record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save Role")

        if not success:
            self._show_error(result)
            return

        self.saved_role = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
