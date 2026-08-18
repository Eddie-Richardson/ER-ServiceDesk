# ER-ServiceDesk/desktop/server_backup_worker.py

"""
Triggers a database backup on the Server's dedicated backup listener
(installer/server_backup_listener.ps1) and writes the returned dump
bytes to the admin-configured networked location, on a background
QThread matching every other network-bound worker in this app.

The Server never writes the backup file anywhere itself -- it streams
the dump bytes back as the HTTP response, and THIS worker (running on
the Client, under the admin's own already-logged-in Windows session)
is what actually writes the file to the network location. This is
deliberate: the Server's listener runs as SYSTEM, which has no network
identity of its own to authenticate against a network share with,
while the admin's own session already has legitimate network access.

Authentication is real Windows credentials (validated server-side via
LogonUser), sent as standard HTTP Basic Auth -- same pattern as
Server Resources, not a bespoke token.
"""

from datetime import datetime
from pathlib import Path

import requests
from PySide6.QtCore import QObject, Signal


class ServerBackupWorker(QObject):
    """
    Requests a fresh backup from the Server and writes it to the
    configured networked location.

    Signals:
        finished(bool, str): Emitted exactly once. First argument is
            success/failure. Second is a message meant to be shown
            directly to the admin -- the saved file's full path on
            success, or an error description on failure.
    """

    finished = Signal(bool, str)

    def __init__(self, server_host: str, username: str, password: str, destination_folder: str):
        """
        Args:
            server_host: The Server's bare hostname/IP (no scheme, no port).
        """
        super().__init__()
        self.server_host = server_host
        self.username = username
        self.password = password
        self.destination_folder = destination_folder

    def run(self):
        """Entry point when this worker is moved to a QThread and started."""
        url = f"http://{self.server_host}:8003/backup/create"
        auth = (self.username, self.password)

        try:
            response = requests.get(url, auth=auth, timeout=300)
        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"Could not reach the server: {e}")
            return

        if response.status_code == 401:
            self.finished.emit(False, "Invalid username or password.")
            return
        if response.status_code != 200:
            message = response.text.strip() or f"Server returned status {response.status_code}."
            self.finished.emit(False, f"Backup failed: {message}")
            return

        filename = f"er-servicedesk-backup-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.dump"
        destination_path = Path(self.destination_folder) / filename

        try:
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            destination_path.write_bytes(response.content)
        except OSError as e:
            self.finished.emit(False, f"Backup was created, but could not be saved to {self.destination_folder}:\n\n{e}")
            return

        self.finished.emit(True, f"Backup saved to:\n{destination_path}")
