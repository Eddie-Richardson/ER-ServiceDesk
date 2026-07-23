# ER-ServiceDesk/desktop/tickets_worker.py

"""
Background worker that loads everything the Tickets window needs.

Runs on a QThread so the window never freezes while loading. Fetches the
ticket list alongside every reference table (statuses, categories, types,
customers, devices) needed to render the list and populate the New/Edit
ticket form's dropdowns, in one pass.
"""

from PySide6.QtCore import QObject, Signal

from desktop import session
from desktop.api_client import (
    ApiError,
    list_customers,
    list_devices,
    list_locations,
    list_ticket_categories,
    list_ticket_statuses,
    list_ticket_types,
    list_tickets,
    list_users,
)


class TicketsDataWorker(QObject):
    """
    Loads tickets and all reference data in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "tickets",
            "statuses", "categories", "types", "customers", "devices",
            "users", "locations", each a list of the corresponding
            records. "users" is empty for non-superuser sessions -- see
            _load_users(). On failure, second argument is a
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
                "statuses": list_ticket_statuses(),
                "categories": list_ticket_categories(),
                "types": list_ticket_types(),
                "customers": list_customers(),
                "devices": list_devices(),
                "locations": list_locations(),
                "tickets": list_tickets(),
                "users": self._load_users(),
            }
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, data)

    def _load_users(self) -> list[dict]:
        """
        Fetches the full user list, but only for superuser sessions --
        the backend's /users router rejects everyone else. Regular
        agents get an empty list here and fall back to self-assignment
        only in the ticket form, which needs no API call at all.

        Returns:
            The full user list for a superuser session, or an empty
            list otherwise (including if the fetch unexpectedly fails --
            the "Assigned To" field degrading to self-only is an
            acceptable fallback, not worth failing the whole window
            load over).
        """
        if not session.is_superuser():
            return []
        try:
            return list_users()
        except ApiError:
            return []
