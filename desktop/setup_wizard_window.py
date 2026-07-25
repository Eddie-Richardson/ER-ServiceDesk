# ER-ServiceDesk/desktop/setup_wizard_window.py

"""
First-run Setup Wizard, shown only when no .env exists yet for this
install.

Three pages, navigated with Next/Back:
  1. Mode selection -- Local (everything on this PC), Server (this PC
     hosts the backend for others), or Client (connect to an existing
     server elsewhere).
  2. Setup form -- Gmail credentials + business name for Local/Server
     (which own a real database and send email); just a server address
     for Client (which owns neither).
  3. Progress -- writes .env, starts Docker, runs migrations and
     seeding (Local/Server), or just health-checks the remote server
     (Client), reusing BackendStartupWorker and DatabaseSetupWorker
     exactly as they already exist elsewhere in this app.

Emits setup_complete once everything succeeds, so main.py can hand off
to the normal startup flow -- which will find a real .env from this
point on and never show this wizard again.
"""

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from desktop import layout
from desktop.backend_manager import BackendStartupWorker
from desktop.database_setup_worker import DatabaseSetupWorker
from desktop.env_writer import write_env_file
from desktop.settings_manager import save_backend_url, save_business_name, save_install_mode

MODE_DESCRIPTIONS = {
    "local": "Everything runs on this PC. The right choice if you're the only one using it.",
    "server": "This PC hosts the shared database for other PCs to connect to.",
    "client": "Connect to a server already set up on another PC.",
}


class SetupWizardWindow(QWidget):
    """First-run setup flow: pick a mode, collect what it needs, then set everything up."""

    setup_complete = Signal()

    def __init__(self, compose_dir: str):
        """
        Args:
            compose_dir: Directory containing docker-compose.yml -- where
                .env gets written, and where Docker Compose commands run from.
        """
        super().__init__()
        self.compose_dir = compose_dir
        self.selected_mode: str | None = None

        self._thread: QThread | None = None
        self._worker = None

        self.setWindowTitle("ER-ServiceDesk Setup")
        self.resize(480, 380)

        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_mode_page())
        self.stack.addWidget(self._build_form_page())
        self.stack.addWidget(self._build_progress_page())

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self.stack)
        self.setLayout(outer_layout)

    # -----------------------------------------------------------------
    # Page 1: mode selection
    # -----------------------------------------------------------------
    def _build_mode_page(self) -> QWidget:
        """Builds the Local/Server/Client selection page."""
        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        page_layout.setSpacing(layout.SPACE_SM)

        title = QLabel("Welcome to ER-ServiceDesk")
        title.setObjectName("title")
        page_layout.addWidget(title)

        subtitle = QLabel("How will this install be used?")
        subtitle.setObjectName("subtitle")
        page_layout.addWidget(subtitle)
        page_layout.addSpacing(layout.SPACE_MD)

        self.mode_button_group = QButtonGroup(self)
        self.mode_radio_buttons: dict[str, QRadioButton] = {}

        for mode in ("local", "server", "client"):
            radio = QRadioButton(mode.capitalize())
            self.mode_button_group.addButton(radio)
            self.mode_radio_buttons[mode] = radio
            page_layout.addWidget(radio)

            description = QLabel(MODE_DESCRIPTIONS[mode])
            description.setObjectName("subtitle")
            description.setWordWrap(True)
            page_layout.addWidget(description)
            page_layout.addSpacing(layout.SPACE_SM)

        self.mode_radio_buttons["local"].setChecked(True)

        page_layout.addStretch()

        next_button = QPushButton("Next")
        next_button.setFixedHeight(layout.BUTTON_HEIGHT)
        next_button.clicked.connect(self._on_mode_next)
        page_layout.addWidget(next_button)

        page.setLayout(page_layout)
        return page

    def _on_mode_next(self):
        """Records the selected mode and advances to the setup form."""
        for mode, radio in self.mode_radio_buttons.items():
            if radio.isChecked():
                self.selected_mode = mode
                break

        self._rebuild_form_page()
        self.stack.setCurrentIndex(1)

    # -----------------------------------------------------------------
    # Page 2: setup form (contents depend on the selected mode)
    # -----------------------------------------------------------------
    def _build_form_page(self) -> QWidget:
        """Builds the (initially empty) form page container -- populated by _rebuild_form_page()."""
        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        page_layout.setSpacing(layout.SPACE_SM)
        page.setLayout(page_layout)
        return page

    def _rebuild_form_page(self):
        """
        Rebuilds the form page's fields to match the selected mode --
        Local/Server need Gmail credentials and a business name (they
        own a real database and send email); Client just needs a
        server address (it owns neither).
        """
        page = self.stack.widget(1)
        old_layout = page.layout()
        while old_layout.count():
            item = old_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        title = QLabel("Server Connection" if self.selected_mode == "client" else "Setup")
        title.setObjectName("title")
        old_layout.addWidget(title)

        self.form_error_label = QLabel("")
        self.form_error_label.setObjectName("subtitle")
        self.form_error_label.setStyleSheet("color: #DC2626;")
        self.form_error_label.setWordWrap(True)
        self.form_error_label.hide()

        if self.selected_mode == "client":
            self.server_address_input = QLineEdit()
            self.server_address_input.setPlaceholderText("http://192.168.1.50:8000")
            self.server_address_input.setFixedHeight(layout.INPUT_HEIGHT)
            for label_text, widget in [("Server Address", self.server_address_input)]:
                field_label = QLabel(label_text)
                field_label.setObjectName("subtitle")
                old_layout.addWidget(field_label)
                old_layout.addWidget(widget)
        else:
            self.gmail_address_input = QLineEdit()
            self.gmail_address_input.setPlaceholderText("yourshop@gmail.com")
            self.gmail_address_input.setFixedHeight(layout.INPUT_HEIGHT)

            self.gmail_app_password_input = QLineEdit()
            self.gmail_app_password_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.gmail_app_password_input.setFixedHeight(layout.INPUT_HEIGHT)

            self.business_name_input = QLineEdit()
            self.business_name_input.setPlaceholderText("Your shop's name")
            self.business_name_input.setFixedHeight(layout.INPUT_HEIGHT)

            for label_text, widget in [
                ("Gmail Address", self.gmail_address_input),
                ("Gmail App Password", self.gmail_app_password_input),
                ("Business Name", self.business_name_input),
            ]:
                field_label = QLabel(label_text)
                field_label.setObjectName("subtitle")
                old_layout.addWidget(field_label)
                old_layout.addWidget(widget)

        old_layout.addWidget(self.form_error_label)
        old_layout.addStretch()

        back_button = QPushButton("Back")
        back_button.setObjectName("secondary")
        back_button.setFixedHeight(layout.BUTTON_HEIGHT)
        back_button.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        old_layout.addWidget(back_button)

        next_button = QPushButton("Next")
        next_button.setFixedHeight(layout.BUTTON_HEIGHT)
        next_button.clicked.connect(self._on_form_next)
        old_layout.addWidget(next_button)

    def _on_form_next(self):
        """Validates the current mode's form, then starts the setup sequence."""
        if self.selected_mode == "client":
            address = self.server_address_input.text().strip().rstrip("/")
            if not address:
                self._show_form_error("Enter the server's address.")
                return
            if not address.startswith("http://") and not address.startswith("https://"):
                self._show_form_error("Address must start with http:// or https://")
                return
            self._client_server_address = address
        else:
            gmail_address = self.gmail_address_input.text().strip()
            gmail_app_password = self.gmail_app_password_input.text().strip()
            business_name = self.business_name_input.text().strip()

            if not gmail_address:
                self._show_form_error("Enter the Gmail address.")
                return
            if not gmail_app_password:
                self._show_form_error("Enter the Gmail app password.")
                return
            if not business_name:
                self._show_form_error("Enter your business name.")
                return

            self._local_gmail_address = gmail_address
            self._local_gmail_app_password = gmail_app_password
            self._local_business_name = business_name

        self.stack.setCurrentIndex(2)
        self._start_setup()

    def _show_form_error(self, message: str):
        """
        Args:
            message: The validation error to show below the form.
        """
        self.form_error_label.setText(message)
        self.form_error_label.show()

    # -----------------------------------------------------------------
    # Page 3: progress
    # -----------------------------------------------------------------
    def _build_progress_page(self) -> QWidget:
        """Builds the progress page shown while setup actually runs."""
        page = QWidget()
        page_layout = QVBoxLayout()
        page_layout.setContentsMargins(
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
            layout.WINDOW_MARGIN, layout.WINDOW_MARGIN,
        )
        page_layout.setSpacing(layout.SPACE_MD)

        self.progress_status_label = QLabel("Setting up...")
        self.progress_status_label.setObjectName("title")
        self.progress_status_label.setWordWrap(True)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)

        page_layout.addStretch()
        page_layout.addWidget(self.progress_status_label)
        page_layout.addWidget(self.progress_bar)
        page_layout.addStretch()

        page.setLayout(page_layout)
        return page

    def _start_setup(self):
        """Kicks off the actual setup sequence for whichever mode was selected."""
        if self.selected_mode == "client":
            self._start_client_setup()
        else:
            self._start_local_or_server_setup()

    def _start_local_or_server_setup(self):
        """
        Local/Server setup: write .env, then start Docker, then run
        migrations and seeding. Chained via each worker's finished
        signal, since these are three genuinely sequential steps.
        """
        self.progress_status_label.setText("Writing configuration...")
        try:
            write_env_file(
                self.compose_dir,
                gmail_address=self._local_gmail_address,
                gmail_app_password=self._local_gmail_app_password,
                business_name=self._local_business_name,
            )
        except OSError as e:
            self._on_setup_failed(f"Couldn't write configuration file.\n\n{e}")
            return

        save_install_mode(self.selected_mode)
        save_backend_url("http://localhost:8000")
        save_business_name(self._local_business_name)

        self._run_backend_startup(skip_docker=False, on_success=self._run_database_setup)

    def _start_client_setup(self):
        """Client setup: just save the server address and confirm it's reachable."""
        save_install_mode("client")
        save_backend_url(self._client_server_address)

        self._run_backend_startup(
            skip_docker=True,
            on_success=self._on_setup_succeeded,
            health_url=f"{self._client_server_address}/health",
        )

    def _run_backend_startup(self, skip_docker: bool, on_success, health_url: str | None = None):
        """
        Args:
            skip_docker: Passed straight through to BackendStartupWorker.
            on_success: Called with no arguments once the backend is healthy.
            health_url: Overrides the default localhost health-check URL.
        """
        self._on_backend_success = on_success

        self._thread = QThread()
        kwargs = {"compose_dir": self.compose_dir, "skip_docker": skip_docker}
        if health_url:
            kwargs["health_url"] = health_url
        self._worker = BackendStartupWorker(**kwargs)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self.progress_status_label.setText)
        self._worker.finished.connect(self._on_backend_startup_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_backend_startup_finished(self, success: bool, message: str):
        """
        Args:
            success: Whether the backend started/responded successfully.
            message: A confirmation on success, or an error on failure.
        """
        if not success:
            self._on_setup_failed(message)
            return
        self._on_backend_success()

    def _run_database_setup(self):
        """Local/Server only: runs migrations and seeding once the backend is confirmed healthy."""
        self._thread = QThread()
        self._worker = DatabaseSetupWorker(compose_dir=self.compose_dir)
        self._worker.moveToThread(self._thread)

        self._thread.started.connect(self._worker.run)
        self._worker.status_changed.connect(self.progress_status_label.setText)
        self._worker.finished.connect(self._on_database_setup_finished)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self._thread.start()

    def _on_database_setup_finished(self, success: bool, message: str):
        """
        Args:
            success: Whether migrations and seeding completed successfully.
            message: A confirmation on success, or an error on failure.
        """
        if not success:
            self._on_setup_failed(message)
            return
        self._on_setup_succeeded()

    def _on_setup_succeeded(self):
        """Setup finished successfully -- signal main.py to move on to the normal startup flow."""
        self.progress_status_label.setText("Setup complete!")
        self.progress_bar.setRange(0, 1)
        self.progress_bar.setValue(1)
        self.setup_complete.emit()

    def _on_setup_failed(self, message: str):
        """
        Args:
            message: What went wrong, shown directly to the user. Sends
                them back to the form page to correct anything and retry,
                rather than leaving them stuck on a dead progress screen.
        """
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Icon.Critical)
        box.setWindowTitle("Setup Failed")
        box.setText(message)
        box.exec()

        self.stack.setCurrentIndex(1)
