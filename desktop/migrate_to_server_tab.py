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
from desktop.settings_manager import save_backend_url, save_install_mode


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

        Every step here is best-effort -- a failure partway through
        (e.g. a locked file) shouldn't prevent the mode switch, which
        is the one step that actually matters for this PC to stop
        acting as a Local install going forward.
        """
        compose_dir = get_compose_dir()

        try:
            subprocess.run(["docker-compose", "down", "-v"], cwd=compose_dir, timeout=60)
        except Exception:
            pass

        for item in ("docker-compose.yml", "Dockerfile", "requirements.txt", "alembic.ini", "app", "alembic", ".env"):
            item_path = os.path.join(compose_dir, item)
            try:
                if item in ("app", "alembic"):
                    shutil.rmtree(item_path, ignore_errors=True)
                else:
                    os.remove(item_path)
            except Exception:
                pass

        try:
            shutil.rmtree(get_env_backup_dir(), ignore_errors=True)
        except Exception:
            pass

        address = self.address_input.text().strip()
        save_install_mode("client")
        save_backend_url(f"http://{address}:8000")

        QMessageBox.information(
            self,
            "Migration Complete",
            "This PC has been switched to Client mode. Please restart "
            "ER-ServiceDesk for this to take effect.",
        )
