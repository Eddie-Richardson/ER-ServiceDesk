# ER-ServiceDesk/desktop/database_backup_worker.py

"""
Runs a real pg_dump on a background QThread, matching the same
pattern BackendStartupWorker and MigrateToServerWorker already use
elsewhere in this app, so the GUI never freezes while a genuinely
large database is being dumped.

This uses the exact same dump mechanism as Migrate to Server's own
data transfer, but for a completely different purpose: producing a
real, persistent file the shop owner keeps and manages themselves,
rather than an internal, ephemeral transfer that gets deleted right
after use.
"""

import os
import subprocess
from datetime import datetime

from PySide6.QtCore import QObject, Signal

from desktop.app_paths import get_compose_dir


class DatabaseBackupWorker(QObject):
    """
    Dumps the local database to a timestamped file in the given folder.

    Signals:
        status_changed(str): Human-readable progress update.
        finished(bool, str): Emitted exactly once -- success/failure,
            and either the saved file's full path or an error message.
    """

    status_changed = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, destination_folder: str):
        """
        Args:
            destination_folder: Where the timestamped backup file should be written.
        """
        super().__init__()
        self.destination_folder = destination_folder
        self.compose_dir = get_compose_dir()

    def run(self):
        """Entry point when this worker is moved to a QThread and started."""
        self.status_changed.emit("Backing up database...")

        filename = f"er-servicedesk-backup-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.dump"
        destination_path = os.path.join(self.destination_folder, filename)

        # Custom format (-Fc), matching Migrate to Server's own dump --
        # this is what lets the file later be loaded back with
        # pg_restore if it's ever actually needed for real recovery.
        try:
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "pg_dump", "-U", "postgres", "-Fc", "erservicedesk"],
                cwd=self.compose_dir,
                capture_output=True,
                timeout=300,
            )
        except FileNotFoundError:
            self.finished.emit(False, "Could not create a backup -- Docker was not found on this machine.")
            return
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Creating the backup took too long (over 5 minutes). Please try again.")
            return

        if result.returncode != 0:
            self.finished.emit(False, f"Backup failed:\n\n{result.stderr.decode(errors='replace')}")
            return

        try:
            os.makedirs(self.destination_folder, exist_ok=True)
            with open(destination_path, "wb") as f:
                f.write(result.stdout)
        except OSError as e:
            self.finished.emit(
                False,
                f"The backup was created, but could not be saved to "
                f"{self.destination_folder}:\n\n{e}",
            )
            return

        self.finished.emit(True, f"Backup saved to:\n{destination_path}")
