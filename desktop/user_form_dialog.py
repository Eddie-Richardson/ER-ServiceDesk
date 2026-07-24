# ER-ServiceDesk/desktop/user_form_dialog.py

"""
Dialog for creating a new user or editing an existing one.

Roles are a small, fixed set (typically 4-5), and a user can hold
several at once -- plain checkboxes fit that better than the popup-
style multi-select filter built for table filtering elsewhere in this
app; this is data entry, not filtering a list.

No password field anywhere here, by design. On create, the backend
generates a temp password and emails it to the account -- the admin
never sees or chooses it. On edit, password changes go through the
separate Reset Password button, which does the same thing (generate +
email a new temp password, force a change on next login) rather than
letting an admin type a value in directly.

There's no delete button here either, deliberately: hard-deleting a
user who's referenced elsewhere (e.g. a ticket's assigned_to) is a real
data-integrity risk. Deactivating via the Active checkbox is the safe,
reversible alternative -- their account stops working, but historical
records referencing them stay intact.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from desktop import layout
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.reset_password_worker import ResetPasswordWorker
from desktop.user_save_worker import UserSaveWorker


class UserFormDialog(QDialog):
    """
    Modal dialog for creating or editing a user account.

    Pass `user=None` to create a new account, or an existing user dict
    to edit one. On a successful save, the dialog closes itself and the
    saved user record is available via `self.saved_user`.
    """

    def __init__(self, user: dict | None, roles: list[dict], user_roles: list[dict], parent=None):
        """
        Args:
            user: An existing user dict to edit, or None to create a
                new one.
            roles: Every role in the system, for the checkbox list.
            user_roles: Every user-role assignment in the system; this
                dialog filters it down to just this user's own links
                when editing, to know which checkboxes start checked
                and what needs to change on save.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.user = user
        self.roles = roles
        self.saved_user: dict | None = None

        self.my_current_links = (
            [link for link in user_roles if link["user_id"] == user["id"]] if user else []
        )

        self._thread: QThread | None = None
        self._worker: UserSaveWorker | None = None
        self._reset_thread: QThread | None = None
        self._reset_worker: ResetPasswordWorker | None = None

        self.setWindowTitle("Edit User" if user else "New User")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "UserFormDialog")

        self._build_ui()
        if user:
            self._prefill_from_user(user)

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "UserFormDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self):
        """Builds every field, including one checkbox per role."""
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("First name (required)")
        self.first_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Last name (required)")
        self.last_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (required)")
        self.email_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)

        self.superuser_checkbox = QCheckBox("Superuser (full access, bypasses all role permissions)")

        self.role_checkboxes: dict[int, QCheckBox] = {}

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Save User")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_save)

        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("secondary")
        cancel_button.setFixedHeight(layout.BUTTON_HEIGHT)
        cancel_button.clicked.connect(self.reject)

        self.reset_password_button = None
        if self.user:
            self.reset_password_button = QPushButton("Reset Password")
            self.reset_password_button.setObjectName("secondary")
            self.reset_password_button.setFixedHeight(layout.BUTTON_HEIGHT)
            self.reset_password_button.clicked.connect(self._attempt_reset_password)

        for label_text, widget in [
            ("First Name", self.first_name_input),
            ("Last Name", self.last_name_input),
            ("Email", self.email_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.active_checkbox)
        outer_layout.addWidget(self.superuser_checkbox)

        roles_label = QLabel("Roles")
        roles_label.setObjectName("subtitle")
        outer_layout.addWidget(roles_label)
        for role in self.roles:
            checkbox = QCheckBox(self._prettify_role_name(role["name"]))
            self.role_checkboxes[role["id"]] = checkbox
            outer_layout.addWidget(checkbox)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)
        if self.reset_password_button:
            outer_layout.addWidget(self.reset_password_button)
        outer_layout.addWidget(cancel_button)

        self.setLayout(outer_layout)

    def _prettify_role_name(self, name: str) -> str:
        """
        Args:
            name: A role's raw backend name, e.g. "front_desk".

        Returns:
            A display-friendly version, e.g. "Front Desk".
        """
        return name.replace("_", " ").title()

    # -----------------------------------------------------------------
    # Prefill (edit mode)
    # -----------------------------------------------------------------
    def _prefill_from_user(self, user: dict):
        """
        Args:
            user: The user dict being edited.
        """
        self.first_name_input.setText(user.get("first_name", ""))
        self.last_name_input.setText(user.get("last_name", ""))
        self.email_input.setText(user.get("email", ""))
        self.active_checkbox.setChecked(user.get("is_active", True))
        self.superuser_checkbox.setChecked(user.get("is_superuser", False))

        my_role_ids = {link["role_id"] for link in self.my_current_links}
        for role_id, checkbox in self.role_checkboxes.items():
            checkbox.setChecked(role_id in my_role_ids)

    # -----------------------------------------------------------------
    # Reset Password
    # -----------------------------------------------------------------
    def _attempt_reset_password(self):
        """
        Confirms with the admin before proceeding -- this immediately
        invalidates the user's current password, so it shouldn't happen
        from an accidental click.
        """
        confirmed = QMessageBox.question(
            self,
            "Reset Password",
            f"This will immediately invalidate {self.user['email']}'s current "
            f"password and email them a new temporary one. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirmed != QMessageBox.StandardButton.Yes:
            return

        self.reset_password_button.setEnabled(False)
        self.reset_password_button.setText("Resetting...")

        self._reset_thread = QThread()
        self._reset_worker = ResetPasswordWorker(self.user["id"])
        self._reset_worker.moveToThread(self._reset_thread)

        self._reset_thread.started.connect(self._reset_worker.run)
        self._reset_worker.finished.connect(self._on_reset_password_finished)
        self._reset_worker.finished.connect(self._reset_thread.quit)
        self._reset_worker.finished.connect(self._reset_worker.deleteLater)
        self._reset_thread.finished.connect(self._reset_thread.deleteLater)

        self._reset_thread.start()

    def _on_reset_password_finished(self, success: bool, result):
        """
        Args:
            success: Whether the reset succeeded.
            result: The updated user record on success, or a
                human-readable error message on failure.
        """
        self.reset_password_button.setEnabled(True)
        self.reset_password_button.setText("Reset Password")

        if not success:
            self._show_error(result)
            return

        QMessageBox.information(
            self,
            "Password Reset",
            f"A new temporary password was emailed to {self.user['email']}.",
        )

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_save(self):
        """Validates the form, then starts the save request on a background thread."""
        payload, error = self._build_payload()
        if error:
            self._show_error(error)
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        desired_role_ids = {
            role_id for role_id, checkbox in self.role_checkboxes.items() if checkbox.isChecked()
        }
        user_id = self.user["id"] if self.user else None

        self._thread = QThread()
        self._worker = UserSaveWorker(payload, desired_role_ids, user_id, self.my_current_links)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_save_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _build_payload(self) -> tuple[dict, str]:
        """
        Returns:
            A (payload, error_message) tuple. error_message is empty if
            validation passed.
        """
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        email = self.email_input.text().strip()

        if not first_name or not last_name:
            return {}, "Enter both a first and last name."
        if not email:
            return {}, "Enter an email address."

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
            "is_active": self.active_checkbox.isChecked(),
            "is_superuser": self.superuser_checkbox.isChecked(),
        }

        return payload, ""

    def _on_save_finished(self, success: bool, result):
        """
        Args:
            success: Whether the save succeeded.
            result: The saved user record on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Save User")

        if not success:
            self._show_error(result)
            return

        self.saved_user = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
