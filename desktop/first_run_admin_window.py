# ER-ServiceDesk/desktop/first_run_admin_window.py

"""
"Create your admin account" screen, shown instead of the normal Login
window exactly once -- on a fresh install, before any account exists
at all. See base_dialog.py's show_login(), which checks
GET /users/first-run-status before deciding which of the two to show.

Once this succeeds, a real superuser account genuinely exists, so this
screen can never show again for the life of this install -- the check
that got someone here in the first place would now come back True.

Synchronous, no QThread -- a small, one-time-ever action, same
reasoning already used for similarly rare, infrequent actions
elsewhere (e.g. PaymentPlanSetupDialog), not something that
justifies a full background-thread worker just for this.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout, session
from desktop.api_client import ApiError


class FirstRunAdminWindow(QWidget):
    """Shown once, on a fresh install with zero existing accounts."""

    login_succeeded = Signal()
    needs_login = Signal(str)

    def __init__(self):
        """Builds the account-creation form inside a centered card panel."""
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Create Admin Account")
        self.setFixedSize(layout.DIALOG_WIDTH, 500)

        card = QWidget()
        card.setObjectName("card")

        title = QLabel("ER-ServiceDesk")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Create the first admin account to get started")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)

        self.first_name_input = QLineEdit()
        self.first_name_input.setPlaceholderText("First name (required)")
        self.first_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.last_name_input = QLineEdit()
        self.last_name_input.setPlaceholderText("Last name (required)")
        self.last_name_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email (required)")
        self.email_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password (8+ chars, upper/lower/number/special)")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(layout.INPUT_HEIGHT)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Confirm password")
        self.confirm_password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.confirm_password_input.setFixedHeight(layout.INPUT_HEIGHT)
        self.confirm_password_input.returnPressed.connect(self._attempt_create)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()

        self.create_button = QPushButton("Create Account")
        self.create_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.create_button.clicked.connect(self._attempt_create)

        self.login_instead_button = QPushButton("Already have an account? Log in instead")
        self.login_instead_button.setObjectName("secondary")
        self.login_instead_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.login_instead_button.clicked.connect(self._go_to_login)

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(
            layout.CARD_PADDING, layout.CARD_PADDING,
            layout.CARD_PADDING, layout.CARD_PADDING,
        )
        card_layout.setSpacing(layout.SPACE_SM)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(layout.SPACE_MD)
        card_layout.addWidget(self.first_name_input)
        card_layout.addWidget(self.last_name_input)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.confirm_password_input)
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(layout.SPACE_SM)
        card_layout.addWidget(self.create_button)
        card_layout.addWidget(self.login_instead_button)
        card.setLayout(card_layout)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.addWidget(card)
        self.setLayout(outer_layout)

        self.first_name_input.setFocus()

    def _attempt_create(self):
        """Validates the form client-side, then submits if everything passes."""
        first_name = self.first_name_input.text().strip()
        last_name = self.last_name_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        if not first_name or not last_name:
            self._show_error("Enter both a first and last name.")
            return
        if not email:
            self._show_error("Enter an email address.")
            return
        if password != confirm_password:
            self._show_error("Password and confirmation don't match.")
            return

        strength_error = self._password_strength_error(password)
        if strength_error:
            self._show_error(strength_error)
            return

        self._set_form_enabled(False)
        self.error_label.hide()
        self.create_button.setText("Creating account...")

        try:
            api_client.create_first_run_admin({
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "password": password,
            })
        except ApiError as e:
            self._set_form_enabled(True)
            self.create_button.setText("Create Account")
            self._show_error(str(e))
            return

        # The account now genuinely exists -- log straight in with the
        # same credentials just entered, rather than making the person
        # retype what they typed seconds ago on a normal Login screen.
        try:
            token = api_client.login(email, password)
        except api_client.LoginError:
            # However unlikely (the account was just created with
            # these exact credentials), the account is real either
            # way -- clicking "Create Account" again here would only
            # ever fail now with "an account already exists", leaving
            # the person genuinely stuck. Hand off to a real,
            # pre-filled Login window instead of letting that happen.
            self.needs_login.emit(email)
            return

        session.set_token(token)
        self.login_succeeded.emit()

    def _go_to_login(self):
        """
        Manual escape hatch -- regardless of what specifically might
        go wrong on this screen, or whether an account was already
        created in a previous attempt, someone should always have a
        direct, obvious way to reach the normal Login window instead
        of being stuck here.
        """
        self.needs_login.emit(self.email_input.text().strip())

    def _password_strength_error(self, password: str) -> str:
        """
        Returns:
            A human-readable error message if the password fails any
            requirement, or an empty string if it passes all of them.
            Identical to ChangePasswordDialog's own check -- the
            backend enforces the same requirements regardless, but a
            specific, immediate message here is far more helpful than
            waiting for the server to reject a weak password.
        """
        if len(password) < 8:
            return "Password must be at least 8 characters."
        if not any(c.isupper() for c in password):
            return "Password must include at least one uppercase letter."
        if not any(c.islower() for c in password):
            return "Password must include at least one lowercase letter."
        if not any(c.isdigit() for c in password):
            return "Password must include at least one number."
        if not any(not c.isalnum() for c in password):
            return "Password must include at least one special character."
        return ""

    def _set_form_enabled(self, enabled: bool):
        """Enables or disables every field and both buttons, used to prevent double-submission while a request is in flight."""
        self.first_name_input.setEnabled(enabled)
        self.last_name_input.setEnabled(enabled)
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.confirm_password_input.setEnabled(enabled)
        self.create_button.setEnabled(enabled)
        self.login_instead_button.setEnabled(enabled)

    def _show_error(self, message: str):
        """Displays an inline error message below the form fields."""
        self.error_label.setText(message)
        self.error_label.show()
