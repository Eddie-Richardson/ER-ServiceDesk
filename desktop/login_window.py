# ER-ServiceDesk/desktop/login_window.py
# Placeholder Login window.
#
# This is intentionally minimal -- just enough to confirm the startup flow
# (backend auto-start -> health check -> Login) works end to end. The real
# login form (email/password fields, calling POST /auth/login, storing the
# JWT) is built separately as its own task.

from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class LoginWindow(QWidget):
    """Placeholder window shown once the backend is confirmed healthy."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ER-ServiceDesk - Login")
        self.setFixedSize(420, 200)

        label = QLabel("Backend is ready.\n\n(Login form goes here.)")
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)
