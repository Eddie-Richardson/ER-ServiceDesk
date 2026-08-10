# ER-ServiceDesk/desktop/migrate_to_server_tab.py

"""
Settings tab for migrating this Local install's data to a Server.

Superuser-only, same as every other tab in this window -- gated by
the Dashboard before Settings is ever opened. Consistent with how this
whole project is actually used: a Local install is realistically a
single shop owner who's already an admin on their own PC, which is
exactly the person expected to trigger a migration.

The actual data transfer runs on a background thread via
MigrateToServerWorker, matching the exact same QThread wiring pattern
StartupWindow already uses elsewhere in this app. This tab's own job
is collecting the server address and token, requiring explicit
confirmation before anything irreversible happens, and -- once the
admin confirms the migration looks correct -- tearing down the local
install and switching this PC to Client mode.
"""

import os
import shutil
import subprocess
import sys
from datetime import datetime

from PySide6.QtCore import QThread
from PySide6.QtWidgets import (
    QFormLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.app_paths import get_compose_dir, get_env_backup_dir
from desktop.migrate_to_server_worker import MigrateToServerWorker


class MigrateToServerTab(QWidget):
    """Collects a server address/token, runs the migration, and handles local teardown on confirmation."""

    def __init__(self):
        """Builds the form, status label, and Start Migration button."""
        super().__init__()
        self._thread: QThread | None = None
        self._worker: MigrateToServerWorker | None = None
        self._build_ui()

    def _build_ui(self):
        """Builds the warning text, input form, status label, and button."""
        layout = QVBoxLayout()

        warning = QLabel(
            "This permanently moves this installation's data to a server. "
            "Once complete, this PC switches to Client mode, and this "
            "data no longer lives here."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)

        form = QFormLayout()
        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g. 192.168.1.50")
        form.addRow("Server Address:", self.address_input)

        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Shown once on the server's installer at setup time")
        form.addRow("Migration Token:", self.token_input)
        layout.addLayout(form)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.start_button = QPushButton("Start Migration")
        self.start_button.clicked.connect(self._on_start_clicked)
        layout.addWidget(self.start_button)

        layout.addStretch()
        self.setLayout(layout)

    def _on_start_clicked(self):
        """Validates input, confirms with the admin, then starts the migration worker."""
        address = self.address_input.text().strip()
        token = self.token_input.text().strip()

        if not address or not token:
            QMessageBox.warning(
                self,
                "Missing Information",
                "Please enter both the server address and the migration token.",
            )
            return

        confirm = QMessageBox.question(
            self,
            "Confirm Migration",
            f"This sends this PC's entire database to the server at "
            f"{address}, then, once you confirm the result looks "
            f"correct, permanently removes Docker and all local data "
            f"from this PC and switches it to Client mode.\n\n"
            f"This cannot be undone. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return

        self.start_button.setEnabled(False)
        self.status_label.setText("Starting migration...")

        self._thread = QThread()
        self._worker = MigrateToServerWorker(address, token)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self.status_label.setText)
        self._worker.finished.connect(self._on_migration_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_migration_finished(self, success: bool, message: str):
        """
        Handles the worker's final result -- a hard failure just shows
        the error; any other outcome (including the "sent, but
        couldn't verify yet" case) asks the admin to explicitly
        confirm before doing anything irreversible to this PC.

        Args:
            success: Whether the data transfer itself succeeded. Can
                be True even if the post-migration health check
                couldn't confirm the server's up yet -- see message
                for what actually happened.
            message: Always meant to be shown directly to the admin.
        """
        self.start_button.setEnabled(True)

        if not success:
            self.status_label.setText("Migration failed.")
            QMessageBox.critical(self, "Migration Failed", message)
            return

        self.status_label.setText(message)

        proceed = QMessageBox.question(
            self,
            "Complete Migration?",
            message + "\n\nIf everything looks correct on the server "
            "(try logging into it directly to confirm), click Yes to "
            "remove Docker and all local data from this PC and switch "
            "it to Client mode. This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            self.status_label.setText(
                "Migration data was sent, but local teardown was not "
                "confirmed. You can complete it later from this tab."
            )
            return

        self._teardown_and_switch_to_client()

    def _teardown_and_switch_to_client(self):
        """
        Removes Docker containers/volumes and every local backend
        file, deletes the .env backup folder (a liability once this PC
        no longer needs those credentials -- the same reasoning
        already applied to the installer's own uninstall cleanup), and
        switches this PC's registry values to Client mode pointed at
        the server.

        Every cleanup step here is best-effort -- a failure partway
        through (e.g. a locked file) shouldn't prevent the mode
        switch, which is the one step that actually matters for this
        PC to stop acting as a Local install going forward. Logged
        directly (not silently swallowed) though -- a real test showed
        this whole method reporting success while every step inside it
        had actually failed, with genuinely no way to tell afterward.

        The mode switch itself is handled differently from the rest:
        install_mode/backend_url are SystemScope (HKEY_LOCAL_MACHINE)
        settings, confirmed directly in settings_manager.py's own
        docstrings to require admin rights to write -- but this app
        never runs elevated day to day, by design, so regular
        non-admin employees can use it too. A real test proved this
        was silently breaking the one moment it actually needed
        elevation: the write here never actually persisted, so
        restarting the app kept showing it as Local, still pointed at
        localhost, with no error shown anywhere. Fixed by re-launching
        this same exe with a hidden flag via PowerShell's
        Start-Process -Verb RunAs -Wait, triggering a real UAC prompt
        for just this one privileged write, then waiting for it to
        finish and confirming it actually succeeded before telling the
        admin the switch is done.
        """
        debug_log_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-teardown-debug-log.txt")

        def debug_log(message: str):
            with open(debug_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{datetime.now().isoformat()} - {message}\n")

        debug_log("=== _teardown_and_switch_to_client starting ===")
        compose_dir = get_compose_dir()

        try:
            result = subprocess.run(
                ["docker-compose", "down", "-v"], cwd=compose_dir, shell=True, timeout=60
            )
            debug_log(f"docker-compose down -v: returncode={result.returncode}")
        except Exception as exc:
            debug_log(f"docker-compose down -v FAILED: {type(exc).__name__}: {exc}")

        for item in ("docker-compose.yml", "Dockerfile", "requirements.txt", "alembic.ini", "app", "alembic", ".env", "RestoreDatabaseLocal.exe"):
            item_path = os.path.join(compose_dir, item)
            try:
                if item in ("app", "alembic"):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
                debug_log(f"Removed {item_path}")
            except Exception as exc:
                debug_log(f"Failed to remove {item_path}: {type(exc).__name__}: {exc}")

        try:
            shutil.rmtree(get_env_backup_dir(), ignore_errors=True)
            debug_log(f"Removed env backup dir: {get_env_backup_dir()}")
        except Exception as exc:
            debug_log(f"Failed to remove env backup dir: {type(exc).__name__}: {exc}")

        address = self.address_input.text().strip()
        backend_url = f"http://{address}:8000"
        exe_path = sys.executable
        ps_command = (
            f'$p = Start-Process -FilePath "{exe_path}" '
            f'-ArgumentList "--set-client-mode", "{backend_url}" '
            f'-Verb RunAs -Wait -PassThru; '
            f'exit $p.ExitCode'
        )
        debug_log(f"Launching elevated for registry write: exe_path={exe_path!r}, backend_url={backend_url!r}")

        try:
            elevated_result = subprocess.run(["powershell", "-Command", ps_command], timeout=120)
            debug_log(f"Elevated registry write: returncode={elevated_result.returncode}")
        except Exception as exc:
            debug_log(f"Elevated registry write FAILED to launch: {type(exc).__name__}: {exc}")
            elevated_result = None

        if elevated_result is None or elevated_result.returncode != 0:
            QMessageBox.critical(
                self,
                "Mode Switch Failed",
                "Local files and Docker were cleaned up, but switching "
                "this PC to Client mode failed -- either the "
                "administrator prompt was cancelled, or the write "
                "itself failed. This PC is not yet in Client mode. You "
                "can retry the switch from Settings once ready.",
            )
            return

        QMessageBox.information(
            self,
            "Migration Complete",
            "This PC has been switched to Client mode. Please restart "
            "ER-ServiceDesk for this to take effect.",
        )
