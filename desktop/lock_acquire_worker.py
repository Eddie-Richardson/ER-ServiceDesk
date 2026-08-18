# ER-ServiceDesk/desktop/lock_acquire_worker.py

"""
Background worker that attempts to acquire a check-out lock on a record.

Runs on a QThread so the app never freezes while waiting on the
network round-trip -- this happens right as someone double-clicks a
row, so it needs to feel instant, not like it's blocking the UI.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, LockConflictError, acquire_lock


class LockAcquireWorker(QObject):
    """
    Attempts to acquire a lock in the background.

    Signals:
        finished(bool, str): Emitted once. First argument is success.
            On success, second argument is empty. On failure, second
            argument is a human-readable message -- either who currently
            holds the lock, or a connection/session error.
    """

    finished = Signal(bool, str)

    def __init__(self, entity_type: str, entity_id: int):
        """
        Args:
            entity_type: The kind of record, e.g. "ticket", "customer".
        """
        super().__init__()
        self.entity_type = entity_type
        self.entity_id = entity_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Attempts the lock acquisition and emits `finished` with the
        result. Never raises -- failures are reported through the
        signal instead.
        """
        try:
            acquire_lock(self.entity_type, self.entity_id)
        except (LockConflictError, ApiError) as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, "")
