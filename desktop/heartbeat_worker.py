# ER-ServiceDesk/desktop/heartbeat_worker.py

"""
Background worker that renews the session's access token.

Runs on a QThread so a periodic heartbeat call never has any chance of
freezing the UI, even briefly -- this fires automatically in the
background, not in response to something the person clicked.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, heartbeat


class HeartbeatWorker(QObject):
    """
    Calls the heartbeat endpoint in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is
            success. On success, second argument is the new access
            token string. On failure, second argument is the caught
            ApiError (or SessionExpiredError) itself, not a stringified
            message -- activity_monitor.py reacts to a
            SessionExpiredError here the same as anywhere else.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Never raises -- failures are reported through the signal instead.
        """
        try:
            token = heartbeat()
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, token)
