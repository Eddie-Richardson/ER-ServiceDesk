# ER-ServiceDesk/desktop/asset_save_worker.py

"""
Background worker that creates or updates a single asset.

Runs on a QThread so the New/Edit asset dialog never freezes while
saving. Mirrors the pattern used by TicketSaveWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, create_asset, update_asset


class AssetSaveWorker(QObject):
    """
    Creates a new asset, or updates an existing one, in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved asset record (dict).
            On failure, second argument is the caught ApiError (or
            SessionExpiredError) itself, not a stringified message --
            callers use handle_api_error() to react to it.
    """

    finished = Signal(bool, object)

    def __init__(self, payload: dict, asset_id: int | None = None):
        """
        Args:
            payload: Fields to send, matching AssetCreate (for a new
                asset) or AssetUpdate (for an edit).
            asset_id: The asset's id if editing, or None to create a
                new asset.
        """
        super().__init__()
        self.payload = payload
        self.asset_id = asset_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the asset and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.asset_id is None:
                result = create_asset(self.payload)
            else:
                result = update_asset(self.asset_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, result)
