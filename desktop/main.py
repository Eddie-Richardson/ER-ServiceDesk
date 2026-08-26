# ER-ServiceDesk/desktop/main.py

"""
Entry point for the ER-ServiceDesk desktop application.

Flow on launch:
  0. For Local and Server modes only, confirm .env is available --
     restoring it from the backup location first if it's missing from
     the main install but present there (see env_recovery.py). Client
     mode is deliberately skipped here -- it never has .env at all by
     design (the installer itself never writes one for Client). Setup
     itself (all three modes, and everything each one needs) is
     entirely the Inno installer's job now, not this app's; by the
     time this exe ever runs, .env is expected to already exist for
     Local/Server. If it's missing from both locations there, show a
     clear error and stop rather than crash partway through startup
     with a confusing traceback.
  1. Show the startup splash screen.
  2. It starts the Docker backend stack (or, for a Client-mode install,
     just health-checks the configured remote server) and polls until
     healthy.
  3. On success, the splash screen closes and the Login window opens.
  4. On failure, the splash screen shows the error with a Retry option.
"""

import sys
import os
import faulthandler

# Qt cross-thread faults (QObject::setParent, recursive repaint, active
# painter warnings) can terminate the process with ZERO Python-level
# traceback -- a genuine low-level (C++) fault, not a Python exception,
# so none of the try/except protection elsewhere in the app can catch
# it. faulthandler is specifically built for exactly this: it prints a
# real stack trace at the moment of a crash like this, even one
# Python's own exception handling has no visibility into at all.
#
# faulthandler.enable() defaults to writing to sys.stderr, which isn't
# just invisible in a console=False PyInstaller build -- it's
# genuinely None there, not a valid stream at all -- so the default
# call raises "RuntimeError: sys.stderr is None" before the app can
# even open. Targeting an explicit log file instead avoids that
# entirely, and the whole thing is wrapped in its own try/except so
# nothing about this diagnostic feature can ever prevent the app from
# starting, regardless of what goes wrong opening it.
try:
    _faulthandler_log_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-crash-log.txt")
    _faulthandler_log_file = open(_faulthandler_log_path, "a", encoding="utf-8")
    faulthandler.enable(file=_faulthandler_log_file)
except Exception:
    pass

# faulthandler above only catches low-level (C++) faults -- a genuine
# unhandled Python exception is a different kind of event entirely, and
# in this console=False build, Python's own default exception handling
# tries to print to sys.stderr, which is None here (not just
# invisible), so it fails just as silently as the app itself would.
# This replaces the default handler with one that writes the real
# traceback to its own log file, so an unhandled exception leaves an
# actual trace to diagnose from instead of the app just disappearing.
try:
    _python_crash_log_path = os.path.join(os.environ.get("TEMP", "."), "er-servicedesk-python-crash-log.txt")

    def _log_unhandled_exception(exc_type, exc_value, exc_traceback):
        import traceback
        from datetime import datetime
        try:
            with open(_python_crash_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n[{datetime.now().isoformat(timespec='seconds')}]\n")
                traceback.print_exception(exc_type, exc_value, exc_traceback, file=f)
        except Exception:
            pass

    sys.excepthook = _log_unhandled_exception
except Exception:
    pass

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from desktop.base_dialog import show_login
from desktop.activity_monitor import ActivityMonitor
from desktop.app_paths import get_compose_dir, get_env_backup_dir, get_icon_path
from desktop.env_recovery import ensure_env_available
from desktop.settings_manager import (
    get_saved_theme,
    get_install_mode,
    save_backend_url,
    save_backup_location,
    save_install_mode,
)
from desktop.startup_window import StartupWindow
from desktop.theme import get_stylesheet

COMPOSE_DIR = get_compose_dir()
ENV_BACKUP_DIR = get_env_backup_dir()
ICON_PATH = get_icon_path()


def main():
    """
    Builds the QApplication, applies the saved theme and app icon,
    confirms .env is available for Local/Server (restoring from backup
    if needed), and wires up the startup -> login -> dashboard ->
    (logout ->) login window flow.
    """
    # Hidden entry point, no GUI at all -- just writes the client-mode
    # registry values and exits. install_mode/backend_url are
    # SystemScope (HKEY_LOCAL_MACHINE) settings, which require admin
    # rights to write (see settings_manager.py) -- but this app never
    # runs elevated day to day, by design, so regular non-admin
    # employees can use it too. The one moment this app actually needs
    # elevation is completing a Local-to-Server migration, which
    # switches this PC to Client mode. Rather than require the whole
    # app to run elevated, migrate_to_server_tab.py re-launches this
    # same exe with this flag via PowerShell's
    # Start-Process -Verb RunAs -Wait, triggering a real UAC prompt for
    # just this one privileged write, then waits for it to finish.
    if len(sys.argv) >= 3 and sys.argv[1] == "--set-client-mode":
        backend_url = sys.argv[2]
        try:
            save_install_mode("client")
            save_backend_url(backend_url)
            sys.exit(0)
        except Exception:
            sys.exit(1)

    # Same pattern and same reason as --set-client-mode above --
    # backup_location is also a SystemScope (HKEY_LOCAL_MACHINE)
    # setting, requiring admin rights to write, but the app never runs
    # elevated day to day. database_backup_tab.py re-launches this same
    # exe with this flag via Start-Process -Verb RunAs -Wait to perform
    # just this one privileged write.
    if len(sys.argv) >= 3 and sys.argv[1] == "--set-backup-location":
        backup_location = sys.argv[2]
        try:
            save_backup_location(backup_location)
            sys.exit(0)
        except Exception:
            sys.exit(1)

    app = QApplication(sys.argv)

    # Created once, lives for the app's entire lifetime (main() itself
    # doesn't return until the app quits, so this local reference is
    # genuinely sufficient to keep it alive -- no need for the
    # QApplication-attribute pattern used below, which exists
    # specifically for windows that get replaced multiple times
    # during the app's life). Does nothing at all until a real
    # session exists -- see activity_monitor.py's own docstring.
    activity_monitor = ActivityMonitor(app)

    # Setting this on the QApplication (rather than per-window) makes it
    # the default for every window that doesn't explicitly override it
    # -- one line covers the title bar icon everywhere, including
    # windows built after this point in the app's lifecycle.
    app.setWindowIcon(QIcon(ICON_PATH))

    # Apply the saved theme before any window is constructed, so nothing
    # ever flashes unstyled or in the wrong theme on launch.
    app.setStyleSheet(get_stylesheet(get_saved_theme()))

    # Setup (all three modes, and everything each one needs) is the Inno
    # installer's job now, not this app's -- so .env is expected to
    # already exist by the time this exe ever runs, for Local/Server.
    # Client mode never has .env at all by design (it only talks to a
    # remote server over HTTP, using the install_mode/backend_url
    # registry values instead) -- skipping this check for Client is
    # what actually lets it reach start_normal_flow() below, where
    # BackendStartupWorker does the check that's actually correct for
    # Client: whether the configured remote server is reachable.
    if get_install_mode() != "client" and not ensure_env_available(COMPOSE_DIR, ENV_BACKUP_DIR):
        QMessageBox.critical(
            None,
            "Configuration Missing",
            "Configuration file missing. This installation cannot start "
            "until it's restored.\n\n"
            "Do NOT reinstall -- that will erase your existing data. "
            "Restore your saved .env file, or contact support.",
        )
        sys.exit(1)

    def start_normal_flow():
        """Shows the startup splash screen and, once healthy, the Login window."""
        startup_window = StartupWindow(compose_dir=COMPOSE_DIR)

        def on_backend_ready():
            """Called once the backend is confirmed healthy; opens Login and closes the splash screen."""
            show_login()
            startup_window.close()

        startup_window.backend_ready.connect(on_backend_ready)
        startup_window.show()
        # Kept alive on the QApplication itself, same pattern
        # show_login() uses for its own windows -- a plain local
        # variable would go out of scope (and the window with it) the
        # moment start_normal_flow() returns.
        app._startup_window = startup_window

    start_normal_flow()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
