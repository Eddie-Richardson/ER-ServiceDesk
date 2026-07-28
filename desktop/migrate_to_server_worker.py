# ER-ServiceDesk/desktop/migrate_to_server_worker.py

"""
Runs the data-transfer half of a Local-to-Server migration on a
background QThread, matching the same pattern BackendStartupWorker
already uses elsewhere in this app -- so the GUI never freezes during
what could be a genuinely large database dump and upload.

This worker's job ends once the data has actually arrived and the
server's health endpoint has been checked. Deciding whether to proceed
with tearing down the local install and switching this PC to Client
mode is deliberately left to the UI layer (migrate_to_server_tab.py),
which requires the admin's explicit confirmation before doing anything
irreversible -- this worker only ever reports what it found.
"""

import os
import subprocess

import requests
from PySide6.QtCore import QObject, Signal

from desktop.app_paths import get_compose_dir


class MigrateToServerWorker(QObject):
    """
    Sends this PC's database to a Migration Target server and checks
    whether the server comes back up healthy afterward.

    Signals:
        status_changed(str): Human-readable progress update.
        finished(bool, str): Emitted exactly once. First argument is
            whether the migration itself succeeded (data transferred
            without a hard error) -- note this can be True even if the
            post-migration health check couldn't confirm the server is
            up yet, since that's a separate, softer signal reported in
            the message rather than treated as failure. Second argument
            is always a message meant to be shown directly to the admin.
    """

    status_changed = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, server_address: str, migration_token: str):
        """
        Args:
            server_address: The Migration Target server's address, e.g. "192.168.1.50".
            migration_token: The one-time token shown on that server's installer at setup time.
        """
        super().__init__()
        self.server_address = server_address
        self.migration_token = migration_token
        self.compose_dir = get_compose_dir()

    def run(self):
        """Entry point when this worker is moved to a QThread and started."""
        self.status_changed.emit("Backing up local database...")
        dump_path = self._create_dump()
        if dump_path is None:
            return  # failure already reported by _create_dump

        self.status_changed.emit("Sending data to server...")
        if not self._send_migration(dump_path):
            return  # failure already reported by _send_migration

        self.status_changed.emit("Verifying server is responding...")
        server_healthy = self._check_server_health()

        if server_healthy:
            self.finished.emit(True, "Migration completed successfully. The server is up and responding.")
        else:
            self.finished.emit(
                True,
                "Migration data was sent, but Setup could not verify the "
                "server is responding yet -- it may still be restarting "
                "its containers. Please confirm it's reachable (try "
                "logging into it directly) before completing this "
                "migration.",
            )

    def _create_dump(self):
        """
        Runs pg_dump inside the local db container, in the custom
        format (-Fc) that pg_restore requires -- a plain-text dump
        (pg_dump's default) can't be loaded with pg_restore, only with
        psql directly, and the Migration Target's listener specifically
        uses pg_restore.

        Returns:
            The path to the saved dump file, or None on failure (in
            which case `finished` has already been emitted).
        """
        dump_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-migration.dump")

        try:
            result = subprocess.run(
                ["docker-compose", "exec", "-T", "db", "pg_dump", "-U", "postgres", "-Fc", "erservicedesk"],
                cwd=self.compose_dir,
                capture_output=True,
                timeout=300,
            )
        except FileNotFoundError:
            self.finished.emit(False, "Could not create a database backup -- Docker was not found on this machine.")
            return None
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Creating the database backup took too long (over 5 minutes). Please try again.")
            return None

        if result.returncode != 0:
            self.finished.emit(False, f"Database backup failed:\n\n{result.stderr.decode(errors='replace')}")
            return None

        with open(dump_path, "wb") as f:
            f.write(result.stdout)
        return dump_path

    def _read_env_value(self, key: str) -> str:
        """
        Reads a single KEY=value line's value directly out of the
        local .env file -- these values travel to the server as-is
        (the exact same Gmail credentials, business name, and
        SECRET_KEY), matching the original design: only the Postgres
        password needs special reconciliation on the server side,
        since it's baked into Postgres itself rather than being a
        plain config value.
        """
        env_path = os.path.join(self.compose_dir, ".env")
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(key + "="):
                    return line.rstrip("\n").split("=", 1)[1]
        return ""

    def _send_migration(self, dump_path: str) -> bool:
        """
        POSTs the raw dump file as the request body, with everything
        else the server needs to finish the migration carried as
        headers -- deliberately not a multipart upload, matching
        exactly what the server-side listener (migration_listener.ps1)
        expects to receive: the whole body is the dump's raw bytes,
        nothing else.
        """
        headers = {
            "X-Migration-Token": self.migration_token,
            "X-Gmail-Address": self._read_env_value("GMAIL_ADDRESS"),
            "X-Gmail-App-Password": self._read_env_value("GMAIL_APP_PASSWORD"),
            "X-Business-Name": self._read_env_value("BUSINESS_NAME"),
            "X-Secret-Key": self._read_env_value("SECRET_KEY"),
            "X-Postgres-Password": self._read_env_value("POSTGRES_PASSWORD"),
        }
        url = f"http://{self.server_address}:8001/migrate/"

        try:
            with open(dump_path, "rb") as f:
                response = requests.post(url, data=f, headers=headers, timeout=600)
        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"Could not reach the server: {e}")
            return False

        if response.status_code != 200:
            self.finished.emit(False, f"Server rejected the migration:\n\n{response.text}")
            return False

        return True

    def _check_server_health(self) -> bool:
        """Returns whether the server's own health endpoint responds successfully."""
        url = f"http://{self.server_address}:8000/health"
        try:
            response = requests.get(url, timeout=15)
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
