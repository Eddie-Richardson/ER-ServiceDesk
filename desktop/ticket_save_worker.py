# ER-ServiceDesk/desktop/ticket_save_worker.py

"""
Background worker that creates or updates a single ticket.

Runs on a QThread so the New/Edit ticket dialog never freezes while
saving. Mirrors the pattern used by LoginWorker and TicketsDataWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, create_ticket, update_ticket


class TicketSaveWorker(QObject):
    """
    Creates a new ticket, or updates an existing one, in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved ticket record (dict).
            On failure, second argument is a human-readable error message.
    """

    finished = Signal(bool, object)

    def __init__(self, payload: dict, ticket_id: int | None = None):
        """
        Args:
            payload: Fields to send, matching TicketCreate (for a new
                ticket) or TicketUpdate (for an edit).
            ticket_id: The ticket's id if editing, or None to create a
                new ticket.
        """
        super().__init__()
        self.payload = payload
        self.ticket_id = ticket_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the ticket and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.ticket_id is None:
                result = create_ticket(self.payload)
            else:
                result = update_ticket(self.ticket_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)
