# ER-ServiceDesk/desktop/part_save_worker.py

"""
Background worker that creates or updates a single part.

Runs on a QThread so the New/Edit part dialog never freezes while
saving. Mirrors the pattern used by TicketSaveWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, create_part, update_part


class PartSaveWorker(QObject):
    """
    Creates a new part, or updates an existing one, in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved part record (dict).
            On failure, second argument is the caught ApiError (or
            SessionExpiredError) itself, not a stringified message --
            callers use handle_api_error() to react to it.
    """

    finished = Signal(bool, object)

    def __init__(self, payload: dict, part_id: int | None = None):
        """
        Args:
            payload: Fields to send, matching PartCreate (for a new
                part) or PartUpdate (for an edit).
            part_id: The part's id if editing, or None to create a
                new part.
        """
        super().__init__()
        self.payload = payload
        self.part_id = part_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the part and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.part_id is None:
                result = create_part(self.payload)
            else:
                result = update_part(self.part_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, result)
