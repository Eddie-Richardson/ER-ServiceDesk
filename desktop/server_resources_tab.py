# ER-ServiceDesk/desktop/server_resources_tab.py

"""
Settings tab for adjusting the Server VM's resource allocation
remotely -- Client mode only (see settings_window.py's conditional),
since this is the one install mode that already has an ongoing
network connection to a Server to send these commands over, the same
way Migrate to Server sends commands to migration_listener.ps1.

Authenticates with real Windows credentials (validated server-side via
LogonUser, the same mechanism RDP itself uses) rather than a token --
resizing the server later is functionally the same trust level as an
admin RDPing into that machine directly. The password is deliberately
never persisted (QSettings would mean storing it in plaintext on this
PC indefinitely); the admin re-enters it each time this tab is used.
The username is remembered as a convenience, since it isn't sensitive
on its own.

RAM and disk changes apply live, no VM restart. CPU changes require
Hyper-V to briefly stop and restart the VM (Set-VMProcessor is not a
live operation) -- this is the one action here with real, if brief,
downtime, so it gets its own two-step confirmation warning about that
restart specifically, not just the general "are you sure."
"""

from urllib.parse import urlparse

from PySide6.QtCore import QSettings, QThread, QTimer
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from desktop.server_resources_worker import ServerResourcesWorker
from desktop.settings_manager import APP_NAME, ORG_NAME, get_backend_url

USERNAME_REMEMBER_KEY = "server_resources/last_username"


def _user_settings() -> QSettings:
    """Same explicit org/app QSettings pattern settings_manager.py itself uses -- a bare QSettings() wouldn't know this app's org/product name, since main.py never registers it globally."""
    return QSettings(ORG_NAME, APP_NAME)


class ServerResourcesTab(QWidget):
    """Status display plus three independent resize controls (memory, CPU, disk), each backed by its own background worker."""

    def __init__(self):
        """Builds the credential fields, status display, and the three resize controls."""
        super().__init__()
        self.server_host = self._get_server_host()
        self._thread: QThread | None = None
        self._worker: ServerResourcesWorker | None = None
        self._build_ui()
        # Deferred rather than called directly from __init__ -- lets
        # the tab finish being fully constructed and shown before the
        # first network call fires.
        QTimer.singleShot(0, self._on_refresh_clicked)

    def _get_server_host(self) -> str:
        """Extracts the bare host/IP from the saved backend_url (e.g. 'http://192.168.1.50:8000' -> '192.168.1.50')."""
        parsed = urlparse(get_backend_url())
        return parsed.hostname or ""

    def _build_ui(self):
        """Builds the credential row, status group, and the three resize groups."""
        layout = QVBoxLayout()

        cred_form = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setText(_user_settings().value(USERNAME_REMEMBER_KEY, ""))
        cred_form.addRow("Windows Username:", self.username_input)
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        cred_form.addRow("Windows Password:", self.password_input)
        layout.addLayout(cred_form)

        note = QLabel(
            "Use the same Windows account credentials you'd use to "
            "remote into the server directly. This password is never "
            "saved -- you'll need to enter it each time you use this tab."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.status_label = QLabel("Status not loaded yet.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        refresh_button = QPushButton("Refresh Status")
        refresh_button.clicked.connect(self._on_refresh_clicked)
        layout.addWidget(refresh_button)

        # -- Memory --
        memory_group = QGroupBox("Memory")
        memory_layout = QFormLayout()
        self.memory_spin = QSpinBox()
        self.memory_spin.setRange(1, 512)
        self.memory_spin.setSuffix(" GB")
        memory_layout.addRow("New maximum:", self.memory_spin)
        memory_apply = QPushButton("Apply (takes effect immediately, no restart)")
        memory_apply.clicked.connect(self._on_apply_memory)
        memory_layout.addRow(memory_apply)
        memory_group.setLayout(memory_layout)
        layout.addWidget(memory_group)

        # -- CPU --
        cpu_group = QGroupBox("CPU")
        cpu_layout = QFormLayout()
        self.cpu_spin = QSpinBox()
        self.cpu_spin.setRange(1, 128)
        self.cpu_spin.setSuffix(" vCPU")
        cpu_layout.addRow("New count:", self.cpu_spin)
        cpu_apply = QPushButton("Apply (requires a brief server restart)")
        cpu_apply.clicked.connect(self._on_apply_cpu)
        cpu_layout.addRow(cpu_apply)
        cpu_group.setLayout(cpu_layout)
        layout.addWidget(cpu_group)

        # -- Disk --
        disk_group = QGroupBox("Disk")
        disk_layout = QFormLayout()
        self.disk_spin = QSpinBox()
        self.disk_spin.setRange(1, 4000)
        self.disk_spin.setSuffix(" GB")
        disk_layout.addRow("New capacity:", self.disk_spin)
        disk_apply = QPushButton("Apply (grow only -- cannot be undone)")
        disk_apply.clicked.connect(self._on_apply_disk)
        disk_layout.addRow(disk_apply)
        disk_group.setLayout(disk_layout)
        layout.addWidget(disk_group)

        layout.addStretch()
        self.setLayout(layout)

    def _credentials_or_warn(self) -> tuple[str, str] | None:
        """Returns (username, password) if both are filled in, or shows a warning and returns None."""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "Missing Credentials", "Please enter both the Windows username and password.")
            return None
        _user_settings().setValue(USERNAME_REMEMBER_KEY, username)
        return username, password

    def _run_worker(self, action: str, **kwargs):
        """Starts a ServerResourcesWorker on a background thread for the given action."""
        creds = self._credentials_or_warn()
        if creds is None:
            return
        username, password = creds

        self._thread = QThread()
        self._worker = ServerResourcesWorker(self.server_host, username, password, action, **kwargs)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self.status_label.setText("Working...")
        self._thread.start()

    def _on_worker_finished(self, success: bool, message: str, payload: object):
        """
        Args:
            success: Whether the action succeeded.
            message: Shown directly to the admin.
            payload: The parsed status dict for a "status" refresh, else None.
        """
        if success and payload:
            self.status_label.setText(
                f"Current: {payload['memory_max_gb']}GB RAM max, "
                f"{payload['cpu_count']} vCPU, {payload['disk_cap_gb']}GB disk.\n"
                f"Host has: {payload['host_ram_gb']}GB RAM, "
                f"{payload['host_cpu_count']} logical processors, "
                f"{payload['host_free_disk_gb']}GB free disk."
            )
            self.memory_spin.setValue(int(payload["memory_max_gb"]))
            self.cpu_spin.setValue(int(payload["cpu_count"]))
            self.disk_spin.setValue(int(payload["disk_cap_gb"]))
        elif success:
            self.status_label.setText(message)
        else:
            self.status_label.setText("Action failed -- see the message shown.")
            QMessageBox.critical(self, "Action Failed", message)

    def _on_refresh_clicked(self):
        """Fetches current status from the server, if credentials are already filled in."""
        if not self.username_input.text().strip() or not self.password_input.text():
            self.status_label.setText("Enter credentials above, then Refresh Status.")
            return
        self._run_worker("status")

    def _on_apply_memory(self):
        """Applies a new memory maximum -- live, no confirmation needed since it's fully reversible and low-risk."""
        self._run_worker("memory", max_gb=self.memory_spin.value())

    def _on_apply_cpu(self):
        """
        Applies a new vCPU count -- this is the one action here with
        real, if brief, downtime (Set-VMProcessor requires the VM to
        be off), so it gets its own explicit two-step confirmation
        naming that restart specifically, not just a generic "are you
        sure."
        """
        confirm = QMessageBox.question(
            self,
            "Confirm CPU Change",
            f"Changing the server's vCPU count to {self.cpu_spin.value()} requires "
            f"briefly stopping and restarting the server. It will be "
            f"unreachable for a short time while this happens.\n\n"
            f"Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._run_worker("cpu", count=self.cpu_spin.value())

    def _on_apply_disk(self):
        """Applies a new disk capacity -- grow-only and irreversible, so this gets a lighter single confirmation."""
        confirm = QMessageBox.question(
            self,
            "Confirm Disk Change",
            f"Growing the server's disk to {self.disk_spin.value()}GB cannot be "
            f"undone -- disk space can only be increased, never reduced, "
            f"once applied.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self._run_worker("disk", cap_gb=self.disk_spin.value())
