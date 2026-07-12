# ER-ServiceDesk/desktop/login_worker.py

"""
Background worker for the login API call.

Runs on a QThread so a slow or unreachable backend never freezes the
login window. Mirrors the pattern used by BackendStartupWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import LoginError, login


class LoginWorker(QObject):
    """
    Performs the login request in the background.

    Signals:
        finished(bool, str): Emitted once. First argument is success;
            second is either the access token (on success) or a
            human-readable error message (on failure).
    """

    finished = Signal(bool, str)

    def __init__(self, email: str, password: str):
        """
        Args:
            email: The email address to authenticate with.
            password: The plaintext password to authenticate with.
        """
        super().__init__()
        self.email = email
        self.password = password

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Attempts login and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            token = login(self.email, self.password)
        except LoginError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, token)
