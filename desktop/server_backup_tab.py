# ER-ServiceDesk/desktop/server_backup_tab.py

"""
Settings tab for triggering a Server database backup remotely --
Client mode only (see settings_window.py's conditional), same
reasoning as Server Resources: Client is the one install mode with an
ongoing network connection to a Server to send this over.

Authenticates with real Windows credentials (validated server-side via
LogonUser), same pattern as Server Resources -- not a bespoke token.
The password is never persisted; the admin re-enters it each time.
The username and the networked backup location are both remembered
via QSettings, since neither is sensitive on its own.

The backup destination is deliberately a networked location the admin
configures, not the Server itself and not just wherever this Client
happens to be -- a backup that only lives on the machine it's meant to
protect against isn't much of a safety net.
"""

from urllib.parse import urlparse

from PySide6.QtCore import QSettings, QThread, QTimer
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.path_validation import check_path_writable
from desktop.server_backup_worker import ServerBackupWorker
from desktop.settings_manager import APP_NAME, ORG_NAME, get_backend_url

USERNAME_REMEMBER_KEY = "server_backup/last_username"
LOCATION_REMEMBER_KEY = "server_backup/destination_folder"


def _user_settings() -> QSettings:
    """Same explicit org/app QSettings pattern used elsewhere in this app -- a bare QSettings() wouldn't know this app's org/product name, since main.py never registers it globally."""
    return QSettings(ORG_NAME, APP_NAME)


class ServerBackupTab(QWidget):
    """Credential fields, a networked destination picker, and a single 'Back Up Now' action."""

    def __init__(self):
        """Builds the credential fields, destination picker, and backup control."""
        super().__init__()
        self.server_host = self._get_server_host()
        self._thread: QThread | None = None
        self._worker: ServerBackupWorker | None = None
        self._build_ui()

    def _get_server_host(self) -> str:
        """Extracts the bare host/IP from the saved backend_url (e.g. 'http://192.168.1.50:8000' -> '192.168.1.50')."""
        parsed = urlparse(get_backend_url())
        return parsed.hostname or ""

    def _build_ui(self):
        """Builds the credential row, destination picker, and backup button."""
        layout = QVBoxLayout()

        cred_form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setText(_user_settings().value(USERNAME_REMEMBER_KEY, ""))
        cred_form.addRow("Windows Username:", self.username_input)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        cred_form.addRow("Windows Password:", self.password_input)
        layout.addLayout(cred_form)

        cred_note = QLabel(
            "Use the same Windows account credentials you'd use to "
            "remote into the server directly. This password is never "
            "saved -- you'll need to enter it each time you use this tab."
        )
        cred_note.setWordWrap(True)
        layout.addWidget(cred_note)

        location_form = QFormLayout()
        self.location_display = QLineEdit()
        self.location_display.setText(_user_settings().value(LOCATION_REMEMBER_KEY, ""))
        self.location_display.setReadOnly(True)
        location_form.addRow("Backup Location:", self.location_display)
        layout.addLayout(location_form)

        choose_button = QPushButton("Choose Location...")
        choose_button.clicked.connect(self._on_choose_location)
        layout.addWidget(choose_button)

        location_note = QLabel(
            "Choose a genuinely separate networked location -- a NAS, "
            "a network share, or similar. A backup that only lives on "
            "the server itself doesn't protect against the server "
            "failing."
        )
        location_note.setWordWrap(True)
        layout.addWidget(location_note)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.backup_button = QPushButton("Back Up Now")
        self.backup_button.clicked.connect(self._on_backup_clicked)
        layout.addWidget(self.backup_button)

        layout.addStretch()
        self.setLayout(layout)

    def _on_choose_location(self):
        """Opens a folder picker (works for network/UNC paths too) and validates it's genuinely writable before remembering the chosen location."""
        chosen = QFileDialog.getExistingDirectory(self, "Choose Backup Location", self.location_display.text())
        if not chosen:
            return

        writable, error = check_path_writable(chosen)
        if not writable:
            QMessageBox.critical(self, "Location Not Usable", error)
            return

        self.location_display.setText(chosen)
        _user_settings().setValue(LOCATION_REMEMBER_KEY, chosen)

    def _on_backup_clicked(self):
        """Validates inputs and starts the backup worker on a background thread."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        destination = self.location_display.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both the Windows username and password.")
            return
        if not destination:
            QMessageBox.warning(self, "Missing Location", "Please choose a backup location first.")
            return

        _user_settings().setValue(USERNAME_REMEMBER_KEY, username)

        self._thread = QThread()
        self._worker = ServerBackupWorker(self.server_host, username, password, destination)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_backup_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self.backup_button.setEnabled(False)
        self.status_label.setText("Backing up...")
        self._thread.start()

    def _on_backup_finished(self, success: bool, message: str):
        """
        Args:
            success: Whether the backup succeeded.
            message: Shown directly to the admin.
        """
        self.backup_button.setEnabled(True)
        self.status_label.setText(message)
        if not success:
            QMessageBox.critical(self, "Backup Failed", message)
