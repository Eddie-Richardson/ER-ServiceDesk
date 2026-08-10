# ER-ServiceDesk/desktop/lock_gate.py

"""
Reusable "acquire lock, open dialog, release lock" flow.

Every window's edit action follows the same shape: try to lock the
record, and only if that succeeds, open the edit dialog -- then release
the lock once the dialog closes, whether it was saved or cancelled.
Rather than rebuild that acquire/open/release dance in every window,
LockGate does it once; a window just calls attempt_edit() with the
record's type/id and a callback that builds its own dialog.

Not used for creating new records -- a record that doesn't exist yet
has nothing to lock.
"""

from typing import Callable

from PySide6.QtCore import QObject, QThread
from PySide6.QtWidgets import QDialog, QMessageBox, QWidget

from desktop.lock_acquire_worker import LockAcquireWorker
from desktop.lock_release_worker import LockReleaseWorker


class LockGate(QObject):
    """
    Owns the acquire/open/release flow for one window. Create one
    instance per window (in its __init__) and reuse it for every edit
    action that window performs.

    A genuine QObject subclass, not a plain Python class -- confirmed
    via a real, executed reproduction (not just documentation) that
    this matters: without real QObject thread affinity, Qt has no
    valid receiver thread to queue a cross-thread signal delivery to,
    so the connected callback (_on_acquire_finished) could run
    directly on the background worker thread regardless of what
    connection type is requested on the connect() call -- confirmed
    this happens even with an explicit Qt.ConnectionType.QueuedConnection,
    which is NOT enough on its own without a real QObject receiver.
    Every widget that callback then touches (opening the edit dialog
    itself, and anything opened from within it) inherits that same
    wrong-thread context, causing real, repeated crashes.
    """

    def __init__(self, parent: QWidget):
        """
        Args:
            parent: The window this gate belongs to -- used as the
                parent for any "record is locked" message box, and to
                keep worker/thread references alive on the same object
                that owns this gate. Also passed to QObject's own
                __init__ for genuine Qt parenting, which is what
                establishes this gate's own correct thread affinity.
        """
        super().__init__(parent)
        self._parent_widget = parent
        self._acquire_thread: QThread | None = None
        self._acquire_worker: LockAcquireWorker | None = None
        self._release_thread: QThread | None = None
        self._release_worker: LockReleaseWorker | None = None
        self._entity_type: str | None = None
        self._entity_id: int | None = None
        self._open_dialog: Callable[[], QDialog] | None = None
        self._on_closed: Callable[[QDialog], None] | None = None

    def attempt_edit(
        self,
        entity_type: str,
        entity_id: int,
        open_dialog: Callable[[], QDialog],
        on_closed: Callable[[QDialog], None] | None = None,
    ):
        """
        Tries to acquire a lock on the given record. If successful,
        calls open_dialog() to build the dialog, shows it modally,
        releases the lock once it closes, then calls on_closed(dialog)
        so the caller can react to the result (e.g. refresh its list
        only if the dialog was actually saved). If the lock can't be
        acquired, shows who currently holds it and never calls
        open_dialog() or on_closed() at all.

        Args:
            entity_type: The kind of record, e.g. "ticket", "customer".
            entity_id: The record's own primary key.
            open_dialog: A zero-argument callable that constructs and
                returns the edit dialog. Only called after the lock is
                successfully acquired -- building the dialog can be
                expensive (populating dropdowns, etc.), so there's no
                reason to do it for a record we're not allowed to edit.
            on_closed: Optional callable, given the closed dialog
                instance, so the caller can check dialog.result() and
                decide whether to refresh its own data.
        """
        self._entity_type = entity_type
        self._entity_id = entity_id
        self._open_dialog = open_dialog
        self._on_closed = on_closed

        self._acquire_thread = QThread()
        self._acquire_worker = LockAcquireWorker(entity_type, entity_id)
        self._acquire_worker.moveToThread(self._acquire_thread)

        self._acquire_thread.started.connect(self._acquire_worker.run)
        self._acquire_worker.finished.connect(self._on_acquire_finished)
        self._acquire_worker.finished.connect(self._acquire_thread.quit)
        self._acquire_worker.finished.connect(self._acquire_worker.deleteLater)
        self._acquire_thread.finished.connect(self._acquire_thread.deleteLater)

        self._acquire_thread.start()

    def _on_acquire_finished(self, success: bool, message: str):
        """
        Args:
            success: Whether the lock was acquired.
            message: Empty on success; a human-readable reason on
                failure (who holds it, or a connection error).
        """
        if not success:
            QMessageBox.information(self._parent_widget, "Record Locked", message)
            return

        dialog = self._open_dialog()
        dialog.exec()
        self._release()

        if self._on_closed:
            self._on_closed(dialog)

    def _release(self):
        """Fires off a background release for the record just edited."""
        self._release_thread = QThread()
        self._release_worker = LockReleaseWorker(self._entity_type, self._entity_id)
        self._release_worker.moveToThread(self._release_thread)

        self._release_thread.started.connect(self._release_worker.run)
        self._release_worker.finished.connect(self._release_thread.quit)
        self._release_worker.finished.connect(self._release_worker.deleteLater)
        self._release_thread.finished.connect(self._release_thread.deleteLater)

        self._release_thread.start()
