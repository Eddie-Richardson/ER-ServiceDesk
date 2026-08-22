# ER-ServiceDesk/desktop/inventory_worker.py

"""
Background worker that loads everything the Inventory window needs.

Runs on a QThread so the window never freezes while loading. Fetches
assets, parts, asset categories, and locations in one pass -- both tabs
(Assets / Parts) share the same locations lookup, so it's loaded once
here rather than duplicated per tab.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import (
    ApiError,
    list_asset_categories,
    list_assets,
    list_locations,
    list_parts,
)


class InventoryDataWorker(QObject):
    """
    Loads assets, parts, and reference data in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "assets",
            "parts", "categories", "locations". On failure, second
            argument is the caught ApiError (or SessionExpiredError)
            itself, not a stringified message -- callers use
            handle_api_error() to react to it.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches every list this window needs and emits `finished`. Never
        raises -- API failures are reported through the signal instead.
        """
        try:
            data = {
                "categories": list_asset_categories(),
                "locations": list_locations(),
                "assets": list_assets(),
                "parts": list_parts(),
            }
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, data)
