# ER-ServiceDesk/desktop/ticket_save_worker.py

"""
Background worker that creates or updates a single ticket.

Runs on a QThread so the New/Edit ticket dialog never freezes while
saving. Mirrors the pattern used by LoginWorker and TicketsDataWorker.

Also handles the inline "+ Add New Device" case: if the person picked
that instead of an existing device, a new device is created first and
its id is spliced into the ticket payload before the ticket itself is
saved -- one background pass, not two separate save actions the UI has
to sequence.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, create_device, create_ticket, update_ticket


class TicketSaveWorker(QObject):
    """
    Creates a new ticket, or updates an existing one, in the background.
    Optionally creates a new device first if one was supplied.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved ticket record (dict).
            On failure, second argument is a human-readable error message.
    """

    finished = Signal(bool, object)

    def __init__(
        self,
        payload: dict,
        ticket_id: int | None = None,
        new_device_payload: dict | None = None,
    ):
        """
        Args:
            payload: Fields to send, matching TicketCreate (for a new
                ticket) or TicketUpdate (for an edit). If
                new_device_payload is given, this dict's "device_id"
                will be overwritten with the newly created device's id.
            ticket_id: The ticket's id if editing, or None to create a
                new ticket.
            new_device_payload: Fields matching DeviceCreate, if the
                person chose "+ Add New Device" instead of selecting an
                existing one. None if an existing device was selected.
        """
        super().__init__()
        self.payload = payload
        self.ticket_id = ticket_id
        self.new_device_payload = new_device_payload

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Creates the device first if one was supplied, then saves the
        ticket, and emits `finished` with the result. Never raises --
        failures are reported through the signal instead.
        """
        try:
            if self.new_device_payload is not None:
                new_device = create_device(self.new_device_payload)
                self.payload["device_id"] = new_device["id"]

            if self.ticket_id is None:
                result = create_ticket(self.payload)
            else:
                result = update_ticket(self.ticket_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)
