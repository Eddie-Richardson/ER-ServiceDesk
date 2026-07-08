# ER-ServiceDesk/desktop/backend_manager.py
# Backend stack startup and health-check logic.
#
# Runs on a background QThread so the GUI never freezes while Docker
# containers spin up. Responsible for two things only:
#   1. Running `docker compose up -d` in the project's compose directory.
#   2. Polling the FastAPI /health endpoint until it responds, or timing out.
#
# This module has no GUI code in it -- it only emits Qt signals. The actual
# splash-screen UI lives in startup_window.py, which listens to these signals.

import subprocess
import time

import requests
from PySide6.QtCore import QObject, Signal


class BackendStartupWorker(QObject):
    """
    Starts the Docker Compose backend stack and waits for it to become healthy.

    Signals:
        status_changed(str): Human-readable progress update, safe to show
            directly in a UI label (e.g. "Starting Docker containers...").
        finished(bool, str): Emitted exactly once when the process ends.
            First argument is success/failure; second is a message -- either
            a final confirmation or an explanation of what went wrong.
    """

    status_changed = Signal(str)
    finished = Signal(bool, str)

    def __init__(
        self,
        compose_dir: str,
        health_url: str = "http://localhost:8000/health",
        startup_timeout_seconds: int = 90,
        poll_interval_seconds: float = 2.0,
    ):
        """
        Args:
            compose_dir: Directory containing docker-compose.yml. This is
                where `docker compose up -d` will be run from.
            health_url: The backend's health-check endpoint to poll.
            startup_timeout_seconds: How long to keep polling before giving
                up and reporting failure. Docker image builds on first run
                can be slow, so this is intentionally generous.
            poll_interval_seconds: Delay between health-check attempts.
        """
        super().__init__()
        self.compose_dir = compose_dir
        self.health_url = health_url
        self.startup_timeout_seconds = startup_timeout_seconds
        self.poll_interval_seconds = poll_interval_seconds

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.

        Performs the full startup sequence. Never raises -- all failure
        paths are reported through the `finished` signal so the UI thread
        can react without needing a try/except of its own.
        """
        if not self._start_compose_stack():
            return  # failure signal already emitted by the helper

        if not self._wait_for_healthy():
            return  # failure signal already emitted by the helper

        self.finished.emit(True, "Backend is up and running.")

    def _start_compose_stack(self) -> bool:
        """
        Runs `docker compose up -d`. Returns True on success, False on
        failure (after emitting the `finished` signal with details).
        """
        self.status_changed.emit("Starting Docker containers...")

        try:
            result = subprocess.run(
                ["docker", "compose", "up", "-d"],
                cwd=self.compose_dir,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=180,  # image builds/pulls on first run can be slow
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
                "Docker took too long to start the containers (over 3 "
                "minutes). Please check Docker Desktop is running and try "
                "again.",
            )
            return False

        if result.returncode != 0:
            # Docker's own stderr is the most useful detail we can surface --
            # e.g. "Cannot connect to the Docker daemon" or a port conflict.
            detail = result.stderr.strip() or "Unknown error from Docker Compose."
            self.finished.emit(
                False,
                f"Failed to start the backend containers.\n\n{detail}",
            )
            return False

        return True

    def _wait_for_healthy(self) -> bool:
        """
        Polls the health endpoint until it responds successfully or the
        timeout is reached. Returns True on success, False on timeout
        (after emitting the `finished` signal with details).
        """
        self.status_changed.emit("Waiting for backend to become ready...")

        deadline = time.monotonic() + self.startup_timeout_seconds

        while time.monotonic() < deadline:
            try:
                response = requests.get(self.health_url, timeout=3)
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                # Backend isn't accepting connections yet -- expected while
                # containers are still starting up. Just keep polling.
                pass

            time.sleep(self.poll_interval_seconds)

        self.finished.emit(
            False,
            "The backend containers started, but the API never became "
            "ready in time. Check Docker Desktop to see if a container "
            "crashed, or try restarting the app.",
        )
        return False