# ER-ServiceDesk/desktop/tickets_worker.py

"""
Background worker that loads everything the Tickets window needs.

Runs on a QThread so the window never freezes while loading. Fetches the
ticket list alongside every reference table (statuses, categories, types,
customers, devices) needed to render the list and populate the New/Edit
ticket form's dropdowns, in one pass.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import (
    ApiError,
    list_assignable_users,
    list_customers,
    list_devices,
    list_locations,
    list_parts,
    list_ticket_categories,
    list_ticket_statuses,
    list_ticket_types,
    list_tickets,
)


class TicketsDataWorker(QObject):
    """
    Loads tickets and all reference data in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "tickets",
            "statuses", "categories", "types", "customers", "devices",
            "parts", "users", "locations", each a list of the
            corresponding records. "users" is now every active user's
            minimal {"id", "full_name", "is_front_desk"} -- available
            to any authenticated session, not just superusers; see
            api_client.list_assignable_users(). On failure, second
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
                "statuses": list_ticket_statuses(),
                "categories": list_ticket_categories(),
                "types": list_ticket_types(),
                "customers": list_customers(),
                "devices": list_devices(),
                "locations": list_locations(),
                "parts": list_parts(),
                "tickets": list_tickets(),
                "users": list_assignable_users(),
            }
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, data)
