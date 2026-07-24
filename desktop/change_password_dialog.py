# ER-ServiceDesk/desktop/change_password_dialog.py

"""
Dialog for setting a new password when login was blocked by
must_change_password.

Reached only from LoginWindow, right after a login attempt reveals the
account needs a new password -- the current (temp) password is passed
in already, since the person just typed it, so they're not asked to
retype it. On success, the dialog holds the fresh access token
(self.new_token) and closes itself; LoginWindow treats that exactly
like a normal successful login.
"""

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from desktop import layout
from desktop.window_geometry import restore_geometry, save_geometry
from desktop.change_password_worker import ChangePasswordWorker


class ChangePasswordDialog(QDialog):
    """
    Modal dialog for setting a new password.

    On a successful change, the dialog closes itself and the fresh
    access token is available via `self.new_token`.
    """

    def __init__(self, email: str, current_password: str, parent=None):
        """
        Args:
            email: The account's email.
            current_password: The temp (or old) password already
                entered at login -- pre-filled here so it's not
                retyped.
            parent: The parent widget, per normal Qt dialog convention.
        """
        super().__init__(parent)
        self.email = email
        self.new_token: str | None = None

        self._thread: QThread | None = None
        self._worker: ChangePasswordWorker | None = None

        self.setWindowTitle("Set New Password")
        self.setMinimumWidth(layout.DIALOG_WIDTH)
        restore_geometry(self, "ChangePasswordDialog")

        self._build_ui(current_password)

    def closeEvent(self, event):
        """
        Args:
            event: The Qt close event, passed through unchanged.
        """
        save_geometry(self, "ChangePasswordDialog")
        super().closeEvent(event)

    # -----------------------------------------------------------------
    # UI construction
    # -----------------------------------------------------------------
    def _build_ui(self, current_password: str):
        """
        Args:
            current_password: Pre-fills the Current Password field.
        """
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.setSpacing(layout.SPACE_SM)

        title = QLabel("Set New Password")
        title.setObjectName("title")

        subtitle = QLabel(f"Your account ({self.email}) needs a new password before you can continue.")
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        self.current_password_input = QLineEdit(current_password)
        self.current_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.current_password_input.setPlaceholderText("Current password")
        self.current_password_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_input.setPlaceholderText("New password (at least 8 characters)")
        self.new_password_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setPlaceholderText("Confirm new password")
        self.confirm_password_input.setFixedHeight(layout.INPUT_HEIGHT)
        self.confirm_password_input.returnPressed.connect(self._attempt_change)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

        self.save_button = QPushButton("Set Password")
        self.save_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.save_button.clicked.connect(self._attempt_change)

        outer_layout.addWidget(title)
        outer_layout.addWidget(subtitle)
        outer_layout.addSpacing(layout.SPACE_MD)

        for label_text, widget in [
            ("Current Password", self.current_password_input),
            ("New Password", self.new_password_input),
            ("Confirm New Password", self.confirm_password_input),
        ]:
            field_label = QLabel(label_text)
            field_label.setObjectName("subtitle")
            outer_layout.addWidget(field_label)
            outer_layout.addWidget(widget)

        outer_layout.addWidget(self.error_label)
        outer_layout.addSpacing(layout.SPACE_SM)
        outer_layout.addWidget(self.save_button)

        self.setLayout(outer_layout)
        self.new_password_input.setFocus()

    # -----------------------------------------------------------------
    # Save
    # -----------------------------------------------------------------
    def _attempt_change(self):
        """Validates the form, then starts the change request on a background thread."""
        current_password = self.current_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not current_password:
            self._show_error("Enter your current password.")
            return
        if not new_password:
            self._show_error("Enter a new password.")
            return
        if new_password != confirm_password:
            self._show_error("New password and confirmation don't match.")
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Saving...")
        self.error_label.hide()

        self._thread = QThread()
        self._worker = ChangePasswordWorker(self.email, current_password, new_password)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_finished(self, success: bool, result: str):
        """
        Args:
            success: Whether the change succeeded.
            result: A fresh access token on success, or a
                human-readable error message on failure.
        """
        self.save_button.setEnabled(True)
        self.save_button.setText("Set Password")

        if not success:
            self._show_error(result)
            return

        self.new_token = result
        self.accept()

    def _show_error(self, message: str):
        """
        Args:
            message: The error text to show below the form.
        """
        self.error_label.setText(message)
        self.error_label.show()
