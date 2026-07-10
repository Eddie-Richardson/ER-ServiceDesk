# ER-ServiceDesk/desktop/login_window.py
# Real Login window.
#
# Collects email/password, calls POST /auth/login on a background thread,
# and on success stores the JWT in desktop.session for the rest of the
# app to use. Emits login_succeeded so main.py can move on to the next
# window (Dashboard, once it exists) and close this one.

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop import layout, session
from desktop.login_worker import LoginWorker
from desktop.settings_manager import get_saved_theme, save_theme
from desktop.theme import get_stylesheet


class LoginWindow(QWidget):
    """Login window shown once the backend is confirmed healthy."""

    login_succeeded = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Login")
        self.setFixedSize(layout.DIALOG_WIDTH, 340)

        self._thread: QThread | None = None
        self._worker: LoginWorker | None = None

        # --- Card panel -----------------------------------------------
        card = QWidget()
        card.setObjectName("card")

        title = QLabel("ER-ServiceDesk")
        title.setObjectName("title")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("Sign in to continue")
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
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_login_finished(self, success: bool, result: str):
        self._set_form_enabled(True)
        self.login_button.setText("Log In")

        if not success:
            self._show_error(result)
            return

        session.set_token(result)
        self.login_succeeded.emit()

    def _set_form_enabled(self, enabled: bool):
        self.email_input.setEnabled(enabled)
        self.password_input.setEnabled(enabled)
        self.login_button.setEnabled(enabled)

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _current_theme(self) -> str:
        return get_saved_theme()

    def _refresh_toggle_label(self):
        current = self._current_theme()
        next_theme = "dark" if current == "light" else "light"
        self.theme_toggle_button.setText(f"Switch to {next_theme} theme")

    def _toggle_theme(self):
        next_theme = "dark" if self._current_theme() == "light" else "light"
        save_theme(next_theme)

        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(get_stylesheet(next_theme))

        self._refresh_toggle_label()
