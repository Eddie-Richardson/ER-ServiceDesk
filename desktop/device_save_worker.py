# ER-ServiceDesk/desktop/device_save_worker.py

"""
Background worker that updates a single device.

Update-only, deliberately -- device creation stays exclusively in the
Tickets window's "+ Add New Device" flow (a device's first real
appearance in the system is intake, not a separate management screen).
This worker exists so an already-existing device's details (a typo'd
serial number, a corrected model) can be fixed from the Customers
window without touching a ticket.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, update_device


class DeviceSaveWorker(QObject):
    """
    Updates an existing device in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the updated device record
            (dict). On failure, second argument is the caught ApiError
            (or SessionExpiredError) itself, not a stringified message
            -- callers use handle_api_error() to react to it.
    """

    finished = Signal(bool, object)

    def __init__(self, device_id: int, payload: dict):
        """
        Args:
            payload: Fields to update, matching DeviceUpdate.
        """
        super().__init__()
        self.device_id = device_id
        self.payload = payload

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the device and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            result = update_device(self.device_id, self.payload)
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, result)
