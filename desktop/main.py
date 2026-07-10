# ER-ServiceDesk/desktop/main.py
# Entry point for the ER-ServiceDesk desktop application.
#
# Flow on launch:
#   1. Show the startup splash screen.
#   2. It starts the Docker backend stack and polls until healthy.
#   3. On success, the splash screen closes and the Login window opens.
#   4. On failure, the splash screen shows the error with a Retry option.

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from desktop.login_window import LoginWindow
from desktop.logged_in_placeholder import LoggedInPlaceholder
from desktop.settings_manager import get_saved_theme
from desktop.startup_window import StartupWindow
from desktop.theme import get_stylesheet

# docker-compose.yml lives at the project root, one level up from desktop/.
COMPOSE_DIR = str(Path(__file__).resolve().parent.parent)


def main():
    app = QApplication(sys.argv)

    # Apply the saved theme before any window is constructed, so nothing
    # ever flashes unstyled or in the wrong theme on launch.
    app.setStyleSheet(get_stylesheet(get_saved_theme()))

    startup_window = StartupWindow(compose_dir=COMPOSE_DIR)
    window_holder = {}  # avoids windows being garbage-collected once referenced only locally

    def on_backend_ready():
        login_window = LoginWindow()

        def on_login_succeeded():
            next_window = LoggedInPlaceholder()
            next_window.show()
            window_holder["next"] = next_window
            login_window.close()

        login_window.login_succeeded.connect(on_login_succeeded)
        login_window.show()
        window_holder["login"] = login_window
        startup_window.close()

    startup_window.backend_ready.connect(on_backend_ready)
    startup_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
