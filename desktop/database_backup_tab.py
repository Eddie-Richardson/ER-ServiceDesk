# ER-ServiceDesk/desktop/database_backup_tab.py

"""
Settings tab for on-demand database backups.

Superuser-only, same as every other tab in this window -- gated by
the Dashboard before Settings is ever opened.

Local mode only (see settings_window.py's conditional) -- Client has
no local database at all to back up, the same reasoning already
applied to the Migrate to Server tab.

The actual pg_dump runs on a background thread via
DatabaseBackupWorker, matching the same QThread wiring pattern used
throughout this app (StartupWindow, MigrateToServerTab).
"""

import os
import subprocess
import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.database_backup_worker import DatabaseBackupWorker
from desktop.settings_manager import get_backup_location

# A reasonable starting point before the admin has chosen anything --
# not the recommended final choice (see the on-screen note about disk
# failure), just somewhere findable by default.
DEFAULT_BACKUP_FOLDER = os.path.join(os.path.expanduser("~"), "Documents", "ER-ServiceDesk-Backups")


class DatabaseBackupTab(QWidget):
    """Location picker plus a Back Up Now button, running the actual dump on a background thread."""

    def __init__(self):
        """Builds the form, status label, and buttons."""
        super().__init__()
        self._thread: QThread | None = None
        self._worker: DatabaseBackupWorker | None = None
        self._build_ui()

    def _build_ui(self):
        """Builds the disk-failure note, location picker, status label, and backup button."""
        layout = QVBoxLayout()

        note = QLabel(
            "Regularly backing up your database protects against data "
            "loss from hardware failure, accidental deletion, or other "
            "disasters. If the location below is on this same PC's "
            "disk, it will NOT protect you if that disk fails -- an "
            "external drive or network location is strongly recommended."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        location_row = QHBoxLayout()
        self.location_display = QLineEdit()
        self.location_display.setReadOnly(True)
        saved_location = get_backup_location()
        self.location_display.setText(saved_location if saved_location else DEFAULT_BACKUP_FOLDER)
        location_row.addWidget(self.location_display)

        choose_button = QPushButton("Choose Location...")
        choose_button.clicked.connect(self._on_choose_location)
        location_row.addWidget(choose_button)
        layout.addLayout(location_row)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.backup_button = QPushButton("Back Up Now")
        self.backup_button.clicked.connect(self._on_backup_clicked)
        layout.addWidget(self.backup_button)

        layout.addStretch()
        self.setLayout(layout)

    def _on_choose_location(self):
        """Opens a folder picker and, if the admin picks one, saves it as the new default going forward."""
        chosen = QFileDialog.getExistingDirectory(self, "Choose Backup Location", self.location_display.text())
        if chosen:
            self.location_display.setText(chosen)
            self._save_backup_location_elevated(chosen)

    def _on_backup_clicked(self):
        """Starts the backup worker on a background thread."""
        destination = self.location_display.text().strip()
        if not destination:
            self.status_label.setText("Please choose a backup location first.")
            return

        # Persist the current value even if it was only ever the
        # suggested default and never explicitly chosen through the
        # picker -- once they've actually used it, it's their real
        # choice going forward. Only actually triggers an elevated
        # write (and the UAC prompt that comes with it) if this value
        # genuinely isn't already saved -- otherwise every single
        # backup click would prompt for elevation again for no reason.
        if destination != get_backup_location():
            self._save_backup_location_elevated(destination)

        self.backup_button.setEnabled(False)
        self.status_label.setText("Starting backup...")

        self._thread = QThread()
        self._worker = DatabaseBackupWorker(destination)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.finished.connect(self._on_backup_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _save_backup_location_elevated(self, path: str):
        """
        Persists the chosen backup folder via an elevated relaunch of
        this same exe -- backup_location is a SystemScope
        (HKEY_LOCAL_MACHINE) setting, requiring admin rights to write,
        confirmed directly in settings_manager.py's own docstring. This
        app never runs elevated day to day, by design, so a plain
        settings_manager.save_backup_location() call here would
        silently fail to persist for the normal, non-admin case -- the
        exact same bug already caught once for install_mode/
        backend_url and fixed there with this same
        Start-Process -Verb RunAs -Wait pattern
        (migrate_to_server_tab.py's teardown-and-switch-to-Client).

        Args:
            path: The folder path to persist as the saved backup location.
        """
        exe_path = sys.executable
        ps_command = (
            f'$p = Start-Process -FilePath "{exe_path}" '
            f'-ArgumentList "--set-backup-location", "{path}" '
            f'-Verb RunAs -Wait -PassThru; '
            f'exit $p.ExitCode'
        )

        try:
            result = subprocess.run(["powershell", "-Command", ps_command], timeout=120)
        except Exception:
            result = None

        if result is None or result.returncode != 0:
            QMessageBox.warning(
                self,
                "Location Not Saved",
                "This backup location will be used for this backup, but "
                "could not be saved as the default -- either the "
                "administrator prompt was cancelled, or the write "
                "itself failed. You'll need to choose it again next time.",
            )

    def _on_backup_finished(self, success: bool, message: str):
        """
        Args:
            success: Whether the backup was created and saved successfully.
            message: The saved file's full path on success, or an error description on failure.
        """
        self.backup_button.setEnabled(True)
        self.status_label.setText(message)
