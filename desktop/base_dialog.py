# ER-ServiceDesk/desktop/base_dialog.py
# Shared base classes for dialogs and top-level windows
"""
AppDialog and AppWindow are the base classes every ER-ServiceDesk
dialog/window should inherit from instead of QDialog/QWidget
directly. They provide two things centrally, so new windows get both
for free instead of every file reimplementing the same logic:

1. Scrollable content -- call self.set_scrollable_content(widget)
   instead of adding your form/layout straight to the dialog. Content
   taller or wider than the window becomes reachable via scrolling
   instead of running off screen, and the window itself stays
   resizable (the Qt default -- nothing here restricts it).

2. Session-expiry handling -- call self.handle_api_error(error)
   from any _on_..._finished()-style callback instead of showing the
   error directly. A SessionExpiredError (see api_client.py, raised on
   a 401) closes every open window and returns to a fresh Login
   window; any other ApiError is shown as a normal inline message, the
   same as before.

AppDialog and AppWindow don't share a common Qt base class (QDialog
and QWidget aren't related), so the shared logic lives in
_SessionAwareMixin and each class inherits it alongside its own Qt
base.
"""

from PySide6.QtWidgets import QApplication, QDialog, QMessageBox, QScrollArea, QVBoxLayout, QWidget

from desktop import session
from desktop.api_client import ApiError, SessionExpiredError


def force_logout():
    """
    Closes every open window (regardless of nesting) and shows a fresh
    Login window. Standalone (not a method) so both _SessionAwareMixin
    (a session-expired API response, caught from within some specific
    dialog) and activity_monitor.py (an idle timeout, which isn't
    itself a dialog/window instance) can trigger the exact same logout
    flow from two genuinely different situations.
    """
    # Imported here (not at module level) to avoid a circular import:
    # login_window.py imports change_password_dialog.py, which (once
    # migrated to AppDialog) would import this same module -- keeping
    # this lazy keeps base_dialog.py safe to import from anywhere
    # without risk of that cycle.
    from desktop.login_window import LoginWindow

    session.clear()
    QApplication.instance().closeAllWindows()

    login_window = LoginWindow()
    login_window.show()
    # Keep a reference on the QApplication itself so this window
    # isn't garbage-collected the moment this function returns.
    QApplication.instance()._logged_out_login_window = login_window


class _SessionAwareMixin:
    """Shared session-expiry handling for AppDialog and AppWindow."""

    def handle_api_error(self, error: Exception, title: str = "Error", on_other_error=None):
        """
        Args:
            error: The exception caught from a failed API call.
            title: Dialog title to use for the default QMessageBox
                display of a non-expiry error, if on_other_error isn't given.
            on_other_error: Optional callable, given the error's message
                string, for dialogs that show errors inline (e.g.
                self._show_error) instead of the default QMessageBox.
                Not called for a SessionExpiredError.
        """
        if isinstance(error, SessionExpiredError):
            force_logout()
            return

        message = str(error) if isinstance(error, ApiError) else "An unexpected error occurred."
        if on_other_error:
            on_other_error(message)
        else:
            QMessageBox.critical(self, title, message)


class AppDialog(QDialog, _SessionAwareMixin):
    """Base class for form/detail dialogs. See module docstring."""

    def set_scrollable_content(self, content: QWidget):
        """Wraps content in a QScrollArea and makes it this dialog's only child."""
        scroll_area = QScrollArea()
        scroll_area.setWidget(content)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)


class AppWindow(QWidget, _SessionAwareMixin):
    """
    Base class for top-level windows (Dashboard, Tickets, etc.). See
    module docstring.
    """

    def set_scrollable_content(self, content: QWidget):
        """Wraps content in a QScrollArea and makes it this window's only child."""
        scroll_area = QScrollArea()
        scroll_area.setWidget(content)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll_area)
        self.setLayout(outer_layout)
