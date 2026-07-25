# ER-ServiceDesk/desktop/database_setup_worker.py

"""
One-time database setup: runs migrations, then seeds default data.

Kept deliberately separate from backend_manager.BackendStartupWorker,
which stays fast and health-check-only for every normal day-to-day
launch. This worker is only ever invoked once, by the Setup Wizard,
right after the backend is confirmed healthy for the first time --
running migrate+seed on every ordinary launch would be pointless and
slow, even though both steps are individually safe to repeat.

Runs on a background QThread, same as every other Docker-touching
operation in this app, so the wizard's UI never freezes while these
run.
"""

import subprocess

from PySide6.QtCore import QObject, Signal


class DatabaseSetupWorker(QObject):
    """
    Runs `alembic upgrade head` and then the seed script inside the
    running api container.

    Signals:
        status_changed(str): Human-readable progress update, safe to
            show directly in a UI label.
        finished(bool, str): Emitted exactly once when the process
            ends. First argument is success/failure; second is a
            message -- either a final confirmation or an explanation
            of what went wrong.
    """

    status_changed = Signal(str)
    finished = Signal(bool, str)

    def __init__(self, compose_dir: str, timeout_seconds: int = 120):
        """
        Args:
            compose_dir: Directory containing docker-compose.yml. This
                is where `docker compose exec` commands will be run from.
            timeout_seconds: How long to wait for each step before
                giving up and reporting failure.
        """
        super().__init__()
        self.compose_dir = compose_dir
        self.timeout_seconds = timeout_seconds

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.

        Runs migrations, then seeding. Never raises -- all failure
        paths are reported through the `finished` signal so the UI
        thread can react without needing a try/except of its own.
        """
        if not self._run_migrations():
            return  # failure signal already emitted by the helper

        if not self._run_seed():
            return  # failure signal already emitted by the helper

        self.finished.emit(True, "Database set up successfully.")

    def _run_migrations(self) -> bool:
        """
        Runs `docker compose exec api alembic upgrade head`.

        Returns:
            True on success, False on failure (after emitting the
            `finished` signal with details).
        """
        self.status_changed.emit("Setting up the database...")
        return self._run_compose_exec(
            ["alembic", "upgrade", "head"],
            failure_prefix="Failed to set up the database schema.",
        )

    def _run_seed(self) -> bool:
        """
        Runs `docker compose exec api python -m app.db.run_seed`.

        Returns:
            True on success, False on failure (after emitting the
            `finished` signal with details).
        """
        self.status_changed.emit("Loading default data...")
        return self._run_compose_exec(
            ["python", "-m", "app.db.run_seed"],
            failure_prefix="Failed to load default data.",
        )

    def _run_compose_exec(self, command: list[str], failure_prefix: str) -> bool:
        """
        Runs a command inside the api container via `docker compose exec`.

        Args:
            command: The command and its arguments to run inside the
                container, e.g. ["alembic", "upgrade", "head"].
            failure_prefix: Prepended to the error message shown on
                failure, so the user knows which step failed.

        Returns:
            True on success, False on failure (after emitting the
            `finished` signal with details).
        """
        try:
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", "api", *command],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_seconds,
            )
        except FileNotFoundError:
            self.finished.emit(
                False,
                "Docker was not found on this machine. Please make sure "
                "Docker Desktop is installed and running, then try again.",
            )
            return False
        except subprocess.TimeoutExpired:
            self.finished.emit(
                False,
                f"{failure_prefix} The command took too long to finish "
                f"(over {self.timeout_seconds} seconds).",
            )
            return False

        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "Unknown error."
            self.finished.emit(False, f"{failure_prefix}\n\n{detail}")
            return False

        return True
