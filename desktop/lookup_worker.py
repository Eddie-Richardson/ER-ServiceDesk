# ER-ServiceDesk/desktop/lookup_worker.py

"""
Generic background worker that loads a simple lookup table's items.

Parameterized by which list_* function to call (list_locations,
list_asset_categories, etc.) rather than duplicated per lookup type --
Locations, Asset Categories, Ticket Categories, Ticket Statuses, and
Ticket Types are all the same shape, so one worker class covers all
five instead of five near-identical ones.
"""

from typing import Callable

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError


class LookupDataWorker(QObject):
    """
    Loads a lookup table's items in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is
            success. On success, second argument is the list of items.
            On failure, second argument is a human-readable error
            message string.
    """

    finished = Signal(bool, object)

    def __init__(self, list_func: Callable[[], list[dict]]):
        """
        Args:
            list_func: The api_client function to call, e.g.
                list_locations (passed as a reference, not called here).
        """
        super().__init__()
        self.list_func = list_func

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches the list and emits `finished`. Never raises -- API
        failures are reported through the signal instead.
        """
        try:
            items = self.list_func()
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, items)
