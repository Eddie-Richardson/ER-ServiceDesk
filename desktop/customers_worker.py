# ER-ServiceDesk/desktop/customers_worker.py

"""
Background worker that loads everything the Customers window needs.

Runs on a QThread so the window never freezes while loading. Fetches
customers, devices, and locations in one pass -- a customer's devices
are looked up by customer_id from the same in-memory device list rather
than fetched per-customer, since a shop's whole customer/device dataset
is small enough to hold in memory at once.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, list_customers, list_devices, list_locations


class CustomersDataWorker(QObject):
    """
    Loads customers, devices, and locations in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "customers",
            "devices", "locations". On failure, second argument is a
            human-readable error message string.
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
                "customers": list_customers(),
                "devices": list_devices(),
                "locations": list_locations(),
            }
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, data)
