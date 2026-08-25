# ER-ServiceDesk/desktop/activity_monitor.py

"""
Watches for genuine user activity (mouse/keyboard) across the whole
app -- not just API calls -- so a session stays alive only while
someone is actually using the app, and logs out automatically after
real inactivity rather than on a fixed schedule from login.

Created once at app startup (see main.py) and lives for the app's
entire lifetime, surviving across multiple login/logout cycles without
needing to be recreated -- it simply does nothing while
session.current_token() is None (sitting on the Login screen, nothing
to track or heartbeat for).

Two independent things happen on the same periodic timer tick:

1. Heartbeat: if there's been genuine activity since the last one was
   sent, renew the session's token in the background (see
   heartbeat_worker.py) -- well before the token's own expiry, so an
   actively-used session never actually hits that expiry.

2. Idle timeout: if there's been no genuine activity for
   IDLE_TIMEOUT_MINUTES, auto-save any open Notes composer's unsent
   draft (so in-progress work is never silently lost), then force a
   logout -- see base_dialog.force_logout().
"""

from datetime import datetime, timedelta

from PySide6.QtCore import QEvent, QObject, QThread, QTimer

from desktop import session
from desktop.base_dialog import force_logout
from desktop.heartbeat_worker import HeartbeatWorker

# How long of genuine inactivity before logging someone out.
IDLE_TIMEOUT_MINUTES = 15

# How often, at most, to send a heartbeat while there's genuine
# activity -- well under IDLE_TIMEOUT_MINUTES and the token's own
# lifetime, so a transient failure of one heartbeat still leaves
# comfortable room for the next one to succeed before anything expires.
HEARTBEAT_INTERVAL_MINUTES = 2

# How often the timer itself checks activity/idle state. Frequent
# enough to catch the idle threshold with reasonable precision,
# without being wasteful.
CHECK_INTERVAL_SECONDS = 30

# Real user-input event types -- deliberately not watching every Qt
# event (paint events, internal timers, etc.), just genuine activity.
_ACTIVITY_EVENT_TYPES = {
    QEvent.Type.MouseMove,
    QEvent.Type.MouseButtonPress,
    QEvent.Type.KeyPress,
}


class ActivityMonitor(QObject):
    """
    A real QObject subclass, not a plain class -- both the app-wide
    event filter and the QTimer below rely on Qt's own signal/slot and
    event-delivery machinery, which requires genuine QObject identity
    to work correctly.
    """

    def __init__(self, app):
        """
        Args:
            app: The running QApplication instance, to install the
                event filter on.
        """
        super().__init__()
        self._app = app
        self._last_activity_at = datetime.now()
        self._last_heartbeat_at = datetime.now()
        self._heartbeat_thread: QThread | None = None
        self._heartbeat_worker: HeartbeatWorker | None = None

        app.installEventFilter(self)

        self._timer = QTimer(self)
        self._timer.setInterval(CHECK_INTERVAL_SECONDS * 1000)
        self._timer.timeout.connect(self._check_activity)
        self._timer.start()

    def eventFilter(self, watched, event):
        """
        Called by Qt for every event delivered anywhere in the app.
        Only records genuine activity's timestamp -- never consumes or
        blocks the event, so every widget still receives it normally.

        Returns:
            False, always -- this only observes events, never handles them.
        """
        if event.type() in _ACTIVITY_EVENT_TYPES:
            self._last_activity_at = datetime.now()
        return False

    def _check_activity(self):
        """
        Runs on every timer tick. Does nothing at all if no session is
        active (sitting on the Login screen) -- there's nothing to
        heartbeat or time out for someone who isn't logged in yet.
        """
        if session.current_token() is None:
            return

        idle_for = datetime.now() - self._last_activity_at
        if idle_for >= timedelta(minutes=IDLE_TIMEOUT_MINUTES):
            self._handle_idle_timeout()
            return

        activity_since_last_heartbeat = self._last_activity_at > self._last_heartbeat_at
        due_for_heartbeat = datetime.now() - self._last_heartbeat_at >= timedelta(minutes=HEARTBEAT_INTERVAL_MINUTES)
        if activity_since_last_heartbeat and due_for_heartbeat:
            self._send_heartbeat()

    def _send_heartbeat(self):
        """
        Renews the session's token in the background. A heartbeat
        failure doesn't force a logout by itself -- if the session has
        genuinely expired, the next real API call will surface a
        SessionExpiredError through the normal handle_api_error() path
        anyway, so there's no need to duplicate that handling here.
        """
        self._last_heartbeat_at = datetime.now()

        self._heartbeat_thread = QThread()
        self._heartbeat_worker = HeartbeatWorker()
        self._heartbeat_worker.moveToThread(self._heartbeat_thread)

        self._heartbeat_thread.started.connect(self._heartbeat_worker.run)
        self._heartbeat_worker.finished.connect(self._on_heartbeat_finished)
        self._heartbeat_worker.finished.connect(self._heartbeat_thread.quit)
        self._heartbeat_worker.finished.connect(self._heartbeat_worker.deleteLater)
        self._heartbeat_thread.finished.connect(self._heartbeat_thread.deleteLater)

        self._heartbeat_thread.start()

    def _on_heartbeat_finished(self, success: bool, result):
        """
        Args:
            result: On success, the new access token string. On
                failure, the caught ApiError -- silently ignored, per
                _send_heartbeat()'s own reasoning.
        """
        if success:
            session.set_token(result)

    def _handle_idle_timeout(self):
        """
        Auto-saves any open Notes composer's unsent draft first, then
        forces a logout. Imports NotesDialog here (not at module
        level) to avoid a real circular import: notes_dialog.py is
        reachable from ticket_form_dialog.py, which is reachable from
        tickets_window.py, which is reachable from dashboard_window.py
        -- all of which this module would otherwise need to know about
        just to check their type.
        """
        from desktop.notes_dialog import NotesDialog

        for widget in self._app.topLevelWidgets():
            if isinstance(widget, NotesDialog) and widget.has_unsaved_draft():
                widget.auto_save_draft()

        force_logout()
