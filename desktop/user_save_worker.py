# ER-ServiceDesk/desktop/user_save_worker.py

"""
Background worker that creates or updates a user, then syncs their role
assignments to match the desired set.

Runs on a QThread so the New/Edit user dialog never freezes while
saving. Role assignment has no bulk/nested endpoint the way Part's
locations do -- UserRole is a plain join table with one POST per grant
and one DELETE per revoke -- so this worker diffs the user's current
assignments against the desired role_ids after saving the user itself,
and issues exactly the calls needed to reconcile the two.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import (
    ApiError,
    create_user,
    create_user_role,
    delete_user_role,
    update_user,
)


class UserSaveWorker(QObject):
    """
    Creates a new user, or updates an existing one, then reconciles
    their role assignments in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is success.
            On success, second argument is the saved user record (dict).
            On failure, second argument is a human-readable error message.
    """

    finished = Signal(bool, object)

    def __init__(
        self,
        payload: dict,
        desired_role_ids: set[int],
        user_id: int | None = None,
        current_user_role_links: list[dict] | None = None,
    ):
        """
        Args:
            payload: Fields to send, matching UserCreate (for a new
                user) or UserUpdate (for an edit).
            desired_role_ids: The full set of role ids this user should
                end up holding after the save.
            user_id: The user's id if editing, or None to create a new user.
            current_user_role_links: This user's existing UserRole join
                records (each with "id" and "role_id"), used to compute
                which assignments to add vs. remove. Ignored when
                creating a new user, since there's nothing to diff against.
        """
        super().__init__()
        self.payload = payload
        self.desired_role_ids = desired_role_ids
        self.user_id = user_id
        self.current_user_role_links = current_user_role_links or []

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the user, then grants/revokes role assignments to match
        desired_role_ids, and emits `finished` with the result. Never
        raises -- failures are reported through the signal instead.
        """
        try:
            if self.user_id is None:
                result = create_user(self.payload)
                self._grant_roles(result["id"], self.desired_role_ids)
            else:
                result = update_user(self.user_id, self.payload)
                self._sync_roles(self.user_id, self.desired_role_ids)
        except ApiError as e:
            self.finished.emit(False, str(e))
            return

        self.finished.emit(True, result)

    def _grant_roles(self, user_id: int, role_ids: set[int]):
        """
        Args:
            user_id: The newly created user's id.
            role_ids: Every role to grant -- there's nothing to revoke
                for a brand-new user.
        """
        for role_id in role_ids:
            create_user_role(user_id, role_id)

    def _sync_roles(self, user_id: int, desired_role_ids: set[int]):
        """
        Reconciles an existing user's role assignments: grants roles
        that are newly checked, revokes roles that are newly unchecked,
        leaves everything else untouched.

        Args:
            user_id: The user being edited.
            desired_role_ids: The full set of role ids this user should
                end up holding.
        """
        current_role_ids = {link["role_id"] for link in self.current_user_role_links}

        role_ids_to_add = desired_role_ids - current_role_ids
        for role_id in role_ids_to_add:
            create_user_role(user_id, role_id)

        role_ids_to_remove = current_role_ids - desired_role_ids
        for link in self.current_user_role_links:
            if link["role_id"] in role_ids_to_remove:
                delete_user_role(link["id"])
