# ER-ServiceDesk/desktop/login_worker.py

"""
Background worker for the login API call.

Runs on a QThread so a slow or unreachable backend never freezes the
login window. Mirrors the pattern used by BackendStartupWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import LoginError, MustChangePasswordError, login


class LoginWorker(QObject):
    """
    Performs the login request in the background.

    Signals:
        finished(bool, str): Emitted on a normal outcome. First
            argument is success; second is either the access token (on
            success) or a human-readable error message (on failure).
        must_change_password(str): Emitted instead of `finished` when
            credentials are valid but the account must set a new
            password before continuing. Carries the email so the
            caller can move straight to a password-change screen
            without asking the person to retype it.
    """

    finished = Signal(bool, str)
    must_change_password = Signal(str)

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
        Attempts login and emits either `finished` or
        `must_change_password` with the result. Never raises --
        failures are reported through a signal instead.
        """
        try:
            token = login(self.email, self.password)
        except MustChangePasswordError as e:
            self.must_change_password.emit(e.email)
            return
        except LoginError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, token)
