# ER-ServiceDesk/desktop/role_save_worker.py

"""
Background worker that creates or updates a role, then syncs its
permission grants to match the desired set.

Mirrors UserSaveWorker's role-syncing pattern exactly, one level up:
where UserSaveWorker diffs a user's role assignments, this diffs a
role's permission grants. RolePermission has the same shape as
UserRole -- a plain join table, one POST per grant and one DELETE per
revoke, no bulk/nested endpoint.
"""

from PySide6.QtCore import QObject, Signal

from desktop.api_client import (
    ApiError,
    create_role,
    create_role_permission,
    delete_role_permission,
    update_role,
)


class RoleSaveWorker(QObject):
    """
    Creates a new role, or updates an existing one, then reconciles its
    permission grants in the background.

    Signals:
        finished(bool, object): Emitted once. First argument is
            success. On success, second argument is the saved role
            record (dict). On failure, second argument is the caught
            ApiError (or SessionExpiredError) itself, not a
            stringified message -- callers use handle_api_error() to
            react to it.
    """

    finished = Signal(bool, object)

    def __init__(
        self,
        payload: dict,
        desired_permission_ids: set[int],
        role_id: int | None = None,
        current_role_permission_links: list[dict] | None = None,
    ):
        """
        Args:
            payload: {"name": str, "description": str | None}.
            desired_permission_ids: The full set of permission ids this
                role should end up granting after the save.
            role_id: The role's id if editing, or None to create a new role.
            current_role_permission_links: This role's existing
                RolePermission join records (each with "id" and
                "permission_id"), used to compute which grants to add
                vs. remove. Ignored when creating a new role.
        """
        super().__init__()
        self.payload = payload
        self.desired_permission_ids = desired_permission_ids
        self.role_id = role_id
        self.current_role_permission_links = current_role_permission_links or []

    def run(self):
        """
        Entry point when this worker is moved to a QThread and started.
        Saves the role, then grants/revokes permissions to match
        desired_permission_ids, and emits `finished` with the result.
        Never raises -- failures are reported through the signal instead.
        """
        try:
            if self.role_id is None:
                result = create_role(self.payload)
                self._grant_permissions(result["id"], self.desired_permission_ids)
            else:
                result = update_role(self.role_id, self.payload)
                self._sync_permissions(self.role_id, self.desired_permission_ids)
        except ApiError as e:
            self.finished.emit(False, e)
            return

        self.finished.emit(True, result)

    def _grant_permissions(self, role_id: int, permission_ids: set[int]):
        """
        Args:
            role_id: The newly created role's id.
            permission_ids: Every permission to grant -- there's
                nothing to revoke for a brand-new role.
        """
        for permission_id in permission_ids:
            create_role_permission(role_id, permission_id)

    def _sync_permissions(self, role_id: int, desired_permission_ids: set[int]):
        """
        Reconciles an existing role's permission grants: grants
        permissions that are newly checked, revokes permissions that
        are newly unchecked, leaves everything else untouched.

        Args:
            role_id: The role being edited.
            desired_permission_ids: The full set of permission ids this
                role should end up granting.
        """
        current_permission_ids = {
            link["permission_id"] for link in self.current_role_permission_links
        }

        permission_ids_to_add = desired_permission_ids - current_permission_ids
        for permission_id in permission_ids_to_add:
            create_role_permission(role_id, permission_id)

        permission_ids_to_remove = current_permission_ids - desired_permission_ids
        for link in self.current_role_permission_links:
            if link["permission_id"] in permission_ids_to_remove:
                delete_role_permission(link["id"])
