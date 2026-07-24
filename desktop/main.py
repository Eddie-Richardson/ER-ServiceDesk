# ER-ServiceDesk/desktop/main.py

"""
Entry point for the ER-ServiceDesk desktop application.

Flow on launch:
  1. Show the startup splash screen.
  2. It starts the Docker backend stack and polls until healthy.
  3. On success, the splash screen closes and the Login window opens.
  4. On failure, the splash screen shows the error with a Retry option.
"""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from desktop.login_window import LoginWindow
from desktop.dashboard_window import DashboardWindow
from desktop.settings_manager import get_saved_theme
from desktop.startup_window import StartupWindow
from desktop.theme import get_stylesheet

# docker-compose.yml lives at the project root, one level up from desktop/.
COMPOSE_DIR = str(Path(__file__).resolve().parent.parent)
ICON_PATH = str(Path(__file__).resolve().parent / "assets" / "icon.ico")


def main():
    """
    Builds the QApplication, applies the saved theme and app icon, and
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

    startup_window = StartupWindow(compose_dir=COMPOSE_DIR)
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

    def on_backend_ready():
        """Called once the backend is confirmed healthy; opens Login and closes the splash screen."""
        show_login()
        startup_window.close()

    startup_window.backend_ready.connect(on_backend_ready)
    startup_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
