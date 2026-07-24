# ER-ServiceDesk/desktop/change_password_worker.py

"""
Background worker for the self-service password change API call.

Runs on a QThread so the Set New Password dialog never freezes.
Mirrors the pattern used by LoginWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import LoginError, change_password


class ChangePasswordWorker(QObject):
    """
    Performs the password change request in the background.

    Signals:
        finished(bool, str): Emitted once. First argument is success;
            second is either a fresh access token (on success) or a
            human-readable error message (on failure).
    """

    finished = Signal(bool, str)

    def __init__(self, email: str, current_password: str, new_password: str):
        """
        Args:
            email: The account's email.
            current_password: The temp (or old) password.
            new_password: The new password to set.
        """
        super().__init__()
        self.email = email
        self.current_password = current_password
        self.new_password = new_password

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Attempts the change and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            token = change_password(self.email, self.current_password, self.new_password)
        except LoginError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, token)
