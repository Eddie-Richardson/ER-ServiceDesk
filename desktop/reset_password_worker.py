# ER-ServiceDesk/desktop/reset_password_worker.py

"""
Background worker that triggers an admin-initiated password reset.

Runs on a QThread so the Users & Roles form never freezes while the
reset (and its email) is in flight. The admin never sees or chooses the
new password -- the backend generates and emails it directly.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, reset_user_password


class ResetPasswordWorker(QObject):
    """
    Resets an existing user's password in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is
            success. On success, second argument is the updated user
            record (dict). On failure, second argument is a
            human-readable error message.
    """

    finished = Signal(bool, object)

    def __init__(self, user_id: int):
        super().__init__()
        self.user_id = user_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Triggers the reset and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            result = reset_user_password(self.user_id)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)
