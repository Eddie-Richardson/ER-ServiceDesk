# ER-ServiceDesk/desktop/startup_window.py

"""
Splash screen shown while the backend stack is starting up.

Displays a status label and an indeterminate progress bar while
BackendStartupWorker does its work on a background thread. Reads the
saved install mode and backend URL to decide whether Docker needs
starting at all (skipped for Client mode, which has no local Docker)
and which address to health-check (localhost for Local/Server,
whatever remote address was configured for Client). On success, emits
backend_ready so main.py can move on to the Login window. On failure,
shows the error and offers Retry / Quit.
"""

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop.backend_manager import BackendStartupWorker
from desktop.settings_manager import get_backend_url, get_install_mode


class StartupWindow(QWidget):
    """
    Splash screen shown on app launch while the Docker backend starts up.

    Signals:
        backend_ready: Emitted once the backend is confirmed healthy. The
            app's entry point should connect this to opening the Login
            window and closing this splash screen.
    """

    backend_ready = Signal()

    def __init__(self, compose_dir: str):
        """
        Args:
            compose_dir: Directory containing docker-compose.yml, passed
                through to BackendStartupWorker.
        """
        super().__init__()
        self.compose_dir = compose_dir
        self._thread: QThread | None = None
        self._worker: BackendStartupWorker | None = None

        self.setWindowTitle("ER-ServiceDesk")
        self.setFixedSize(420, 160)

        self.status_label = QLabel("Starting up...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # indeterminate -- we don't know ETA

        self.retry_button = QPushButton("Retry")
        self.retry_button.setVisible(False)
        self.retry_button.clicked.connect(self.start_backend)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.retry_button)
        layout.addStretch()
        self.setLayout(layout)

        self.start_backend()

    def start_backend(self):
        """
        Kicks off (or re-kicks-off, on retry) the backend startup sequence
        on a background thread.
        """
        self.retry_button.setVisible(False)
        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Starting up...")

        self._thread = QThread()
        install_mode = get_install_mode()
        backend_url = get_backend_url()
        self._worker = BackendStartupWorker(
            compose_dir=self.compose_dir,
            health_url=f"{backend_url}/health",
            skip_docker=(install_mode == "client"),
        )
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self._on_status_changed)
        self._worker.finished.connect(self._on_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_status_changed(self, message: str):
        self.status_label.setText(message)

    def _on_finished(self, success: bool, message: str):
        """
        Handles the worker's final result: emits backend_ready on
        success, or shows an error dialog with a Retry option on failure.

        Args:
            message: A confirmation message on success, or an error
                description on failure.
        """
        if success:
            self.status_label.setText(message)
            self.backend_ready.emit()
            return

        # Stop the spinner and let the person retry or quit rather than
        # silently leaving them stuck on an indeterminate progress bar.
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(0)
        self.status_label.setText("Startup failed.")
        self.retry_button.setVisible(True)

        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Backend startup failed")
        box.setText(message)
        box.exec()
