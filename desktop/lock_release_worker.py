# ER-ServiceDesk/desktop/lock_release_worker.py

"""
Background worker that releases a check-out lock on a record.

Runs on a QThread so releasing a lock (right as a dialog is closing)
never blocks the UI. Fire-and-forget by design -- there's nothing
useful to show the user if a release has a network hiccup, since the
dialog is already gone; the lock will simply expire on its own via the
normal timeout if the release genuinely never lands.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import release_lock


class LockReleaseWorker(QObject):
    """
    Releases a lock in the background.

    Signals:
        finished(): Emitted once the attempt is done, regardless of
            outcome -- callers typically only need this to know when
            it's safe to clean up the worker/thread, not to react to
            success or failure.
    """

    finished = Signal()

    def __init__(self, entity_type: str, entity_id: int):
        """
        Args:
            entity_type: The kind of record, e.g. "ticket", "customer".
            entity_id: The record's own primary key.
        """
        super().__init__()
        self.entity_type = entity_type
        self.entity_id = entity_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Attempts the release and always emits `finished`, regardless of
        outcome -- see the class docstring for why failures here are
        deliberately not surfaced to the user.
        """
        try:
            release_lock(self.entity_type, self.entity_id)
        except Exception:
            pass
        self.finished.emit()
