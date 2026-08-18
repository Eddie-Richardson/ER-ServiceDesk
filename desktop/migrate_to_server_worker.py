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
import time
from datetime import datetime

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
                "its containers. On the server itself, try running:\n\n"
                "docker ps\n"
                "curl http://localhost:8000/health\n\n"
                "If docker ps shows the containers running and the health "
                "check responds, it's safe to complete this migration.",
            )

    def _create_dump(self):
        """
        Runs pg_dump inside the local db container, in the custom
        format (-Fc) that pg_restore requires -- a plain-text dump
        (pg_dump's default) can't be loaded with pg_restore, only with
        psql directly, and the Migration Target's listener specifically
        uses pg_restore.

        Two separate steps, not one -- streaming pg_dump's output live
        through docker-compose exec relies on Docker's own "hijack"
        mechanism to carry that output back through the exec session,
        and that connection can tear down before any real output comes
        through. This sidesteps that mechanism entirely instead of
        trying to fix it: pg_dump writes its output to a file INSIDE
        the container first (-f), then docker cp pulls that file out
        afterward -- a separate, simpler mechanism that doesn't depend
        on the same live-streaming hijack behavior at all.

        Returns:
            The path to the saved dump file, or None on failure (in
            which case `finished` has already been emitted).
        """
        # Kept permanently, not a temporary debugging aid -- if a
        # migration has issues later, these logs can be pulled
        # directly from the machine rather than needing to ship a
        # special build with logging added first.
        debug_log_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-migration-debug-log.txt")

        def debug_log(message: str):
            with open(debug_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(f"{datetime.now().isoformat()} - {message}\n")

        debug_log(f"_create_dump starting, compose_dir={self.compose_dir}")

        dump_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-migration.dump")
        stderr_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-migration-stderr.txt")
        container_name = "er-servicedesk-app-postgres"
        container_dump_path = "/tmp/er-servicedesk-migration.dump"
        debug_log(f"dump_path={dump_path}, container_dump_path={container_dump_path}")

        dump_cmd = [
            "docker-compose", "exec", "-T", "db",
            "pg_dump", "-U", "postgres", "-Fc", "-f", container_dump_path, "erservicedesk",
        ]
        cp_cmd = ["docker", "cp", f"{container_name}:{container_dump_path}", dump_path]
        debug_log(f"dump_cmd: {dump_cmd!r}")
        debug_log(f"cp_cmd: {cp_cmd!r}")

        try:
            start_time = time.monotonic()
            with open(stderr_path, "wb") as stderr_file:
                dump_result = subprocess.run(
                    dump_cmd,
                    cwd=self.compose_dir,
                    stdout=subprocess.DEVNULL,
                    stderr=stderr_file,
                    shell=True,
                    timeout=300,
                )
        except FileNotFoundError:
            debug_log("FileNotFoundError raised -- docker-compose not found on PATH")
            self.finished.emit(False, "Could not create a database backup -- Docker was not found on this machine.")
            return None
        except subprocess.TimeoutExpired:
            debug_log("TimeoutExpired raised on pg_dump step")
            self.finished.emit(False, "Creating the database backup took too long (over 5 minutes). Please try again.")
            return None

        with open(stderr_path, "rb") as f:
            stderr_content = f.read()
        debug_log(f"pg_dump step completed: returncode={dump_result.returncode}")
        if stderr_content:
            debug_log(f"pg_dump stderr content: {stderr_content.decode(errors='replace')[:2000]}")

        if dump_result.returncode != 0:
            self.finished.emit(False, f"Database backup failed:\n\n{stderr_content.decode(errors='replace')}")
            return None

        # pg_dump can genuinely succeed and the file genuinely exist
        # inside the container, yet a docker cp run immediately
        # afterward can fail to find it -- consistent with a brief
        # WSL2 filesystem-sync lag between the write completing inside
        # the container and it becoming visible to docker cp from
        # outside a moment later. A retry with a short pause covers
        # this without needing to guess at one single "safe" fixed delay.
        cp_result = None
        for attempt in range(5):
            try:
                cp_result = subprocess.run(
                    cp_cmd,
                    cwd=self.compose_dir,
                    capture_output=True,
                    shell=True,
                    timeout=60,
                )
            except subprocess.TimeoutExpired:
                debug_log("TimeoutExpired raised on docker cp step")
                self.finished.emit(False, "Retrieving the database backup took too long. Please try again.")
                return None

            if cp_result.returncode == 0:
                break
            debug_log(f"docker cp attempt {attempt + 1} failed (returncode={cp_result.returncode}), retrying after a short pause...")
            time.sleep(2)

        elapsed = time.monotonic() - start_time
        dump_size = os.path.getsize(dump_path) if os.path.exists(dump_path) else -1
        debug_log(
            f"docker cp step completed: returncode={cp_result.returncode}, "
            f"dump_size_on_disk={dump_size}, total elapsed={elapsed:.3f} seconds"
        )
        if cp_result.stderr:
            debug_log(f"docker cp stderr content: {cp_result.stderr.decode(errors='replace')[:2000]}")

        if cp_result.returncode != 0:
            self.finished.emit(False, f"Database backup failed:\n\n{cp_result.stderr.decode(errors='replace')}")
            return None

        debug_log(f"Dump retrieved successfully via docker cp, {dump_size} bytes")
        return dump_path

    def _read_env_value(self, key: str) -> str:
        """
        Reads a single KEY=value line's value directly out of the
        local .env file -- these values travel to the server as-is
        (SECRET_KEY and DEVICE_ACCOUNT_ENCRYPTION_KEY), matching the
        original design: only the Postgres password needs special
        reconciliation on the server side, since it's baked
        into Postgres itself rather than being a
        plain config value.

        Business name, email credentials, and SMTP/IMAP settings are
        NOT carried this way -- those are real database rows now (see
        app/services/business_info_service.py), so the database dump
        itself already carries them over correctly. No .env
        involvement needed for those at all.

        setup.iss's own WriteEnvFiles wraps every value in double
        quotes (EscapeForEnvFile, escaping literal " and \\ inside
        it) -- this reverses that exactly, so a value comes back
        clean, not as the literal quoted text migration would
        otherwise send as part of the actual data.
        """
        env_path = os.path.join(self.compose_dir, ".env")
        with open(env_path, "r") as f:
            for line in f:
                if line.startswith(key + "="):
                    raw_value = line.rstrip("\n").split("=", 1)[1]
                    if raw_value.startswith('"') and raw_value.endswith('"') and len(raw_value) >= 2:
                        raw_value = raw_value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
                    return raw_value
        return ""

    def _send_migration(self, dump_path: str) -> bool:
        """
        POSTs the raw dump file as the request body, with everything
        else the server needs to finish the migration carried as
        headers -- deliberately not a multipart upload, matching
        exactly what the server-side listener (migration_listener.ps1)
        expects to receive: the whole body is the dump's raw bytes,
        nothing else.

        Reads the whole file into memory first rather than streaming
        it from an open file handle -- passing an open file object to
        requests as data= makes it send the request using chunked
        transfer encoding, since it doesn't know the total size
        upfront, and the server-side listener is built on .NET's
        HttpListener, which has a real, documented limitation
        correctly reading chunked request bodies. Passing raw bytes
        instead gives requests a known, exact size upfront, so it
        sends a normal Content-Length header and avoids chunked
        encoding entirely. Trade-off worth being explicit about: the
        whole dump now sits in memory during the send rather than
        streaming -- genuinely fine for a one-time migration of a
        repair shop's database, not something that would scale to a
        much larger, repeated-transfer use case.
        """
        headers = {
            "X-Migration-Token": self.migration_token,
            "X-Secret-Key": self._read_env_value("SECRET_KEY"),
            "X-Device-Account-Encryption-Key": self._read_env_value("DEVICE_ACCOUNT_ENCRYPTION_KEY"),
            "X-Postgres-Password": self._read_env_value("POSTGRES_PASSWORD"),
        }
        url = f"http://{self.server_address}:8001/migrate/"

        try:
            with open(dump_path, "rb") as f:
                dump_bytes = f.read()
            response = requests.post(url, data=dump_bytes, headers=headers, timeout=600)
        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"Could not reach the server: {e}")
            return False

        if response.status_code != 200:
            self.finished.emit(False, f"Server rejected the migration:\n\n{response.text}")
            return False

        return True

    def _check_server_health(self) -> bool:
        """
        Returns whether the server's own health endpoint responds
        successfully. Retries a few times with a short delay between
        attempts -- the migration listener just recreated the
        server's containers moments before this runs, and they
        realistically need a little time to finish starting back up;
        checking only once made this fail far more often than it
        needed to.
        """
        url = f"http://{self.server_address}:8000/health"
        max_attempts = 5
        delay_seconds = 5

        for attempt in range(max_attempts):
            try:
                response = requests.get(url, timeout=15)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass

            if attempt < max_attempts - 1:
                self.status_changed.emit(
                    f"Verifying server is responding (attempt {attempt + 1} of {max_attempts})..."
                )
                time.sleep(delay_seconds)

        return False
