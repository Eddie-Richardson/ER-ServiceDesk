# ER-ServiceDesk/desktop/customers_worker.py

"""
Background worker that loads everything the Customers window needs.

Runs on a QThread so the window never freezes while loading. Fetches
customers, devices, and locations in one pass -- a customer's devices
are looked up by customer_id from the same in-memory device list rather
than fetched per-customer, since a shop's whole customer/device dataset
is small enough to hold in memory at once. Invoices and tickets are
fetched the same way, for the customer profile's invoice list --
cross-referenced via ticket_id since Invoice has no customer_id of its
own.

Invoices/tickets are fetched separately from customers/devices/
locations and allowed to fail on their own without breaking the whole
window -- /invoices/ requires billing.manage, a different permission
than what gates this window at all (customers.manage), so a user
without billing access should still get a working Customers window,
just with an empty invoice list on each profile rather than the whole
window failing to load.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, list_customers, list_devices, list_locations, list_invoices, list_tickets


class CustomersDataWorker(QObject):
    """
    Loads customers, devices, locations, invoices, and tickets in one
    background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "customers",
            "devices", "locations", "invoices", "tickets". On failure
            (of the customers/devices/locations fetch specifically),
            second argument is a human-readable error message string.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches every list this window needs and emits `finished`. Never
        raises -- API failures on customers/devices/locations are
        reported through the signal instead; a failure fetching
        invoices/tickets specifically (e.g. no billing.manage) degrades
        to empty lists rather than failing the whole window.
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

        try:
            data["invoices"] = list_invoices()
            data["tickets"] = list_tickets()
        except ApiError:
            data["invoices"] = []
            data["tickets"] = []

        self.finished.emit(True, data)
