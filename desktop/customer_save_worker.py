# ER-ServiceDesk/desktop/customer_save_worker.py

"""
Background worker that creates or updates a single customer.

Runs on a QThread so the New/Edit customer dialog never freezes while
saving. Mirrors the pattern used by TicketSaveWorker.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, create_customer, update_customer


class CustomerSaveWorker(QObject):
    """
    Creates a new customer, or updates an existing one, in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved customer record
            (dict). On failure, second argument is a human-readable
            error message.
    """

    finished = Signal(bool, object)

    def __init__(self, payload: dict, customer_id: int | None = None):
        """
        Args:
            payload: Fields to send, matching CustomerCreate (for a new
                customer) or CustomerUpdate (for an edit).
            customer_id: The customer's id if editing, or None to create
                a new customer.
        """
        super().__init__()
        self.payload = payload
        self.customer_id = customer_id

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the customer and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.customer_id is None:
                result = create_customer(self.payload)
            else:
                result = update_customer(self.customer_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)
