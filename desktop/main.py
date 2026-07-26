# ER-ServiceDesk/desktop/main.py

"""
Entry point for the ER-ServiceDesk desktop application.

Flow on launch:
  0. Confirm .env is available -- restoring it from the backup
     location first if it's missing from the main install but present
     there (see env_recovery.py). Setup itself (all three modes --
     Local, Server, Client -- and everything each one needs) is
     entirely the WiX installer's job now, not this app's; by the time
     this exe ever runs, .env is expected to already exist. If it's
     missing from both locations, show a clear error and stop rather
     than crash partway through startup with a confusing traceback.
  1. Show the startup splash screen.
  2. It starts the Docker backend stack (or, for a Client-mode install,
     just health-checks the configured remote server) and polls until
     healthy.
  3. On success, the splash screen closes and the Login window opens.
  4. On failure, the splash screen shows the error with a Retry option.
"""

import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from desktop.login_window import LoginWindow
from desktop.dashboard_window import DashboardWindow
from desktop.app_paths import get_compose_dir, get_env_backup_dir, get_icon_path
from desktop.env_recovery import ensure_env_available
from desktop.settings_manager import get_saved_theme
from desktop.startup_window import StartupWindow
from desktop.theme import get_stylesheet

COMPOSE_DIR = get_compose_dir()
ENV_BACKUP_DIR = get_env_backup_dir()
ICON_PATH = get_icon_path()


def main():
    """
    Builds the QApplication, applies the saved theme and app icon,
    confirms .env is available (restoring from backup if needed), and
    wires up the startup -> login -> dashboard -> (logout ->) login
    window flow.
    """
    app = QApplication(sys.argv)

    # Setting this on the QApplication (rather than per-window) makes it
    # the default for every window that doesn't explicitly override it
    # -- one line covers the title bar icon everywhere, including
    # windows built after this point in the app's lifecycle.
    app.setWindowIcon(QIcon(ICON_PATH))

    # Apply the saved theme before any window is constructed, so nothing
    # ever flashes unstyled or in the wrong theme on launch.
    app.setStyleSheet(get_stylesheet(get_saved_theme()))

    # Setup (all three modes, and everything each one needs) is the WiX
    # installer's job now, not this app's -- so .env is expected to
    # already exist by the time this exe ever runs. This only handles
    # the one thing that can still legitimately go wrong afterward: the
    # file getting deleted or corrupted post-install.
    if not ensure_env_available(COMPOSE_DIR, ENV_BACKUP_DIR):
        QMessageBox.critical(
            None,
            "Configuration Missing",
            "Configuration file missing. This installation cannot start "
            "until it's restored.\n\n"
            "Do NOT reinstall -- that will erase your existing data. "
            "Restore your saved .env file, or contact support.",
        )
        sys.exit(1)

    window_holder = {}  # avoids windows being garbage-collected once referenced only locally

    def show_login():
        """Opens a fresh Login window. Used both at startup and after logout."""
        login_window = LoginWindow()
        login_window.login_succeeded.connect(lambda: show_dashboard(login_window))
        login_window.show()
        window_holder["login"] = login_window

    def show_dashboard(previous_window):
        """
        Opens the Dashboard and closes the window that led here.

        Args:
            previous_window: The Login window to close now that its job is done.
        """
        dashboard = DashboardWindow()
        dashboard.logout_callback = show_login
        dashboard.show()
        window_holder["dashboard"] = dashboard
        previous_window.close()

    def start_normal_flow():
        """Shows the startup splash screen and, once healthy, the Login window."""
        startup_window = StartupWindow(compose_dir=COMPOSE_DIR)

        def on_backend_ready():
            """Called once the backend is confirmed healthy; opens Login and closes the splash screen."""
            show_login()
            startup_window.close()

        startup_window.backend_ready.connect(on_backend_ready)
        startup_window.show()
        window_holder["startup"] = startup_window

    start_normal_flow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
