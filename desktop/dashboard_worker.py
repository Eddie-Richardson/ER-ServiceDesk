# ER-ServiceDesk/desktop/dashboard_worker.py

"""
Background worker that fetches ticket data for the Dashboard.

Runs on a QThread so the Dashboard never freezes while loading. There's
no dedicated stats endpoint on the backend yet, so this fetches the full
ticket and status lists and groups counts client-side -- reasonable at
a single repair shop's ticket volume, and avoids adding a new backend
endpoint for what's still an early desktop build.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, list_ticket_statuses, list_tickets


class DashboardWorker(QObject):
    """
    Loads ticket counts grouped by status.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a list of
            {"name": str, "color": str | None, "count": int} dicts, one
            per status, in the order returned by the backend. On failure,
            second argument is a human-readable error message string.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches statuses and tickets, groups counts by status, and emits
        `finished`. Never raises -- API failures are reported through the
        signal instead.
        """
        try:
            statuses = list_ticket_statuses()
            tickets = list_tickets()
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        counts_by_status_id = {}
        for ticket in tickets:
            status_id = ticket.get("status_id")
            counts_by_status_id[status_id] = counts_by_status_id.get(status_id, 0) + 1

        results = [
            {
                "name": status["name"],
                "color": status.get("color"),
                "count": counts_by_status_id.get(status["id"], 0),
            }
            for status in statuses
        ]

        self.finished.emit(True, results)
