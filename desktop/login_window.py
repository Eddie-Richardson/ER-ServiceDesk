# ER-ServiceDesk/desktop/login_window.py

"""
Real Login window.

Collects email/password, calls POST /auth/login on a background thread,
and on success stores the JWT in desktop.session for the rest of the
app to use. Emits login_succeeded so main.py can move on to the
Dashboard and close this window.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import api_client, layout, session
from desktop.change_password_dialog import ChangePasswordDialog
from desktop.login_worker import LoginWorker
from desktop.settings_manager import get_saved_theme, save_theme, get_business_name, save_business_name
from desktop.theme import get_stylesheet


class LoginWindow(QWidget):
    """Login window shown once the backend is confirmed healthy."""

    login_succeeded = Signal()

    def __init__(self):
        """Builds the login form inside a centered card panel."""
        super().__init__()
        business_name = get_business_name()
        self.setWindowTitle(f"ER-ServiceDesk - {business_name} - Login" if business_name else "ER-ServiceDesk - Login")
        self.setFixedSize(layout.DIALOG_WIDTH, 340)

        self._thread: QThread | None = None
        self._worker: LoginWorker | None = None

        # --- Card panel -----------------------------------------------
        card = QWidget()
        card.setObjectName("card")

        title = QLabel("ER-ServiceDesk")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel(business_name if business_name else "Sign in to continue")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Email")
        self.email_input.setFixedHeight(layout.INPUT_HEIGHT)
        self.email_input.returnPressed.connect(self._attempt_login)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Password")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setFixedHeight(layout.INPUT_HEIGHT)
        self.password_input.returnPressed.connect(self._attempt_login)

        self.error_label = QLabel("")
        self.error_label.setObjectName("subtitle")
        self.error_label.setStyleSheet("color: #DC2626;")  # error red, distinct from theme's muted text
        self.error_label.setWordWrap(True)
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.hide()

        self.login_button = QPushButton("Log In")
        self.login_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.login_button.clicked.connect(self._attempt_login)

        self.theme_toggle_button = QPushButton()
        self.theme_toggle_button.setObjectName("secondary")
        self.theme_toggle_button.setFixedHeight(layout.BUTTON_HEIGHT)
        self.theme_toggle_button.clicked.connect(self._toggle_theme)
        self._refresh_toggle_label()

        card_layout = QVBoxLayout()
        card_layout.setContentsMargins(
            layout.CARD_PADDING, layout.CARD_PADDING,
            layout.CARD_PADDING, layout.CARD_PADDING,
        )
        card_layout.setSpacing(layout.SPACE_SM)
        card_layout.addWidget(title)
        card_layout.addWidget(subtitle)
        card_layout.addSpacing(layout.SPACE_MD)
        card_layout.addWidget(self.email_input)
        card_layout.addWidget(self.password_input)
        card_layout.addWidget(self.error_label)
        card_layout.addSpacing(layout.SPACE_SM)
        card_layout.addWidget(self.login_button)
        card_layout.addWidget(self.theme_toggle_button)
        card.setLayout(card_layout)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        outer_layout.addWidget(card)
        self.setLayout(outer_layout)

        self.email_input.setFocus()

    def _attempt_login(self):
        """
        Validates the form client-side, then starts the login request on
        a background thread if both fields are filled in.
        """
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email or not password:
            self._show_error("Enter both email and password.")
            return

        self._set_form_enabled(False)
        self.error_label.hide()
        self.login_button.setText("Logging in...")

        self._thread = QThread()
        self._worker = LoginWorker(email, password)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_login_finished)
        self._worker.must_change_password.connect(self._on_must_change_password)
        self._worker.finished.connect(self._thread.quit)
        self._worker.must_change_password.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker.must_change_password.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_must_change_password(self, email: str):
        """
        Handles the case where credentials were valid but the account
        must set a new password before continuing. Opens
        ChangePasswordDialog pre-filled with the password already
        typed; on success, proceeds exactly like a normal login.
        """
        self._set_form_enabled(True)
        self.login_button.setText("Log In")

        current_password = self.password_input.text()
        dialog = ChangePasswordDialog(email, current_password, parent=self)
        if dialog.exec():
            session.set_token(dialog.new_token)
            self._cache_business_name_if_needed()
            self.login_succeeded.emit()

    def _cache_business_name_if_needed(self):
        """
        Fetches and caches the shop's display name locally, if not
        already cached -- only ever called after a real, authenticated
        session exists (right after session.set_token()). A Client
        machine never collects this during its own install the way
        Local/Server do, so this is how it ends up with a correct
        value at all: fetched once, right after its very first
        successful login, then cached for every launch after that.
        Safe, cheap no-op for Local/Server too, since their own value
        is already set and this only triggers when nothing's cached.
        """
        if not get_business_name():
            business_name = api_client.fetch_business_name()
            if business_name:
                save_business_name(business_name)

    def _on_login_finished(self, success: bool, result: str):
        """
        Handles the background login worker's result. On success, stores
        the token and emits login_succeeded. On failure, re-enables the
        form and shows the error inline.

        Args:
            result: On success, the JWT access token. On failure, a
                human-readable error message.
        """
        self._set_form_enabled(True)
        self.login_button.setText("Log In")

        if not success:
            self._show_error(result)
            return

        session.set_token(result)
        self._cache_business_name_if_needed()
        self.login_succeeded.emit()

    def _set_form_enabled(self, enabled: bool):
        """
        Enables or disables the form fields and login button, used to
        prevent double-submission while a login request is in flight.
        """
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.login_button.setEnabled(enabled)

    def _show_error(self, message: str):
        """Displays an inline error message below the password field."""
        self.error_label.setText(message)
        self.error_label.show()

    def _current_theme(self) -> str:
        """
        Returns:
            The theme currently saved for this machine, "light" or "dark".
        """
        return get_saved_theme()

    def _refresh_toggle_label(self):
        """Updates the theme toggle button's text to reflect the theme it would switch to."""
        current = self._current_theme()
        next_theme = "dark" if current == "light" else "light"
        self.theme_toggle_button.setText(f"Switch to {next_theme} theme")

    def _toggle_theme(self):
        """
        Flips the theme, persists the choice for this machine, and
        re-applies the stylesheet immediately so the change is visible
        without restarting the app.
        """
        next_theme = "dark" if self._current_theme() == "light" else "light"
        save_theme(next_theme)

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_stylesheet(next_theme))

        self._refresh_toggle_label()
