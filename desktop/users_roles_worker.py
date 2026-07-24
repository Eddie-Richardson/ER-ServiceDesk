# ER-ServiceDesk/desktop/users_roles_worker.py

"""
Background worker that loads everything the Users & Roles window needs.

Runs on a QThread so the window never freezes while loading. Fetches
users, roles, and every user-role assignment in one pass -- the join
table has no server-side filtering, so the full assignment list is
fetched once and filtered client-side by user_id wherever needed.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import ApiError, list_roles, list_user_roles, list_users


class UsersRolesDataWorker(QObject):
    """
    Loads users, roles, and user-role assignments in one background pass.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is a dict with keys "users",
            "roles", "user_roles". On failure, second argument is a
            human-readable error message string.
    """

    finished = Signal(bool, object)

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Fetches every list this window needs and emits `finished`. Never
        raises -- API failures are reported through the signal instead.
        """
        try:
            data = {
                "users": list_users(),
                "roles": list_roles(),
                "user_roles": list_user_roles(),
            }
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, data)
