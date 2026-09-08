# ER-ServiceDesk/desktop/customers_worker.py

"""
Background worker that loads everything the Customers window needs.

Runs on a QThread so the window never freezes while loading. Fetches
customers, devices, and locations in one pass -- a customer's devices
are looked up by customer_id from the same in-memory device list rather
than fetched per-customer, since a shop's whole customer/device dataset
is small enough to hold in memory at once. Invoices, tickets, and
ticket statuses are fetched the same way, for the customer profile's
own invoice and ticket-history sub-tables -- invoices are
cross-referenced via ticket_id since Invoice has no customer_id of its
own, and statuses are used to resolve each ticket's status_id to a
readable name.

Invoices/tickets/statuses are fetched separately from customers/
devices/locations and allowed to fail on their own without breaking the
whole window -- /invoices/ requires billing.manage and
/ticket_statuses/ requires superuser, both different permissions than
what gates this window at all (customers.manage), so a user without
one of those should still get a working Customers window, just with
those specific sub-tables empty on each profile rather than the whole
window failing to load.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, list_customers, list_devices, list_locations, list_invoices, list_tickets, list_ticket_statuses


class CustomersDataWorker(QObject):
    """
    Loads customers, devices, locations, invoices, tickets, and ticket
    statuses in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "customers",
            "devices", "locations", "invoices", "tickets", "statuses".
            On failure (of the customers/devices/locations fetch
            specifically), second argument is the caught ApiError (or
            SessionExpiredError) itself, not a stringified message --
            callers use handle_api_error() to react to it.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches every list this window needs and emits `finished`. Never
        raises -- API failures on customers/devices/locations are
        reported through the signal instead; a failure fetching
        invoices/tickets/statuses specifically (e.g. no billing.manage
        or not a superuser) degrades to empty lists rather than
        failing the whole window.
        """
        try:
            data = {
                "customers": list_customers(),
                "devices": list_devices(),
                "locations": list_locations(),
            }
        except ApiError as e:
            self.finished.emit(False, e)
            return

        try:
            data["invoices"] = list_invoices()
            data["tickets"] = list_tickets()
            data["statuses"] = list_ticket_statuses()
        except ApiError:
            data["invoices"] = []
            data["tickets"] = []
            data["statuses"] = []

        self.finished.emit(True, data)
