# ER-ServiceDesk/desktop/lookup_save_worker.py

"""
Generic background worker that creates, updates, or deletes a simple
lookup table item.

Parameterized by endpoint path rather than duplicated per lookup type --
see lookup_worker.py for the same reasoning.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import (
    ApiError,
    create_lookup_item,
    delete_lookup_item,
    update_lookup_item,
)


class LookupSaveWorker(QObject):
    """
    Creates, updates, or deletes a lookup table item in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is
            success. On a successful create/update, second argument is
            the saved record. On a successful delete, second argument
            is None. On failure, second argument is a human-readable
            error message.
    """

    finished = Signal(bool, object)

    def __init__(
        self,
        endpoint: str,
        payload: dict | None = None,
        item_id: int | None = None,
        delete: bool = False,
    ):
        """
        Args:
            endpoint: The resource path, e.g. "/inventory/locations/".
            payload: Fields to send, for create/update. Ignored if
                delete=True.
            item_id: The record's id, for update or delete. None means
                create a new record.
            delete: If True, deletes item_id instead of saving payload.
        """
        super().__init__()
        self.endpoint = endpoint
        self.payload = payload
        self.item_id = item_id
        self.delete = delete

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Performs the requested operation and emits `finished`. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.delete:
                delete_lookup_item(self.endpoint, self.item_id)
                result = None
            elif self.item_id is None:
                result = create_lookup_item(self.endpoint, self.payload)
            else:
                result = update_lookup_item(self.endpoint, self.item_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)
