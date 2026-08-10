# ER-ServiceDesk/desktop/path_validation.py

"""
Confirms a chosen folder is genuinely usable as a save location --
both database_backup_tab.py (Local) and server_backup_tab.py (Server)
need this identical check for their own location pickers, so it lives
here once rather than duplicated in both.

A folder picker dialog already guarantees the folder EXISTS (you can
only select something you can see), but existing and being genuinely
WRITABLE aren't the same thing -- a read-only network share, or a
folder visible but permission-denied, would pass the picker fine and
then fail silently the first time a real backup actually tries to
write there. This does a real write test (create a small temp file,
then delete it) rather than just checking syntax or visibility, so a
bad location is caught immediately when it's chosen, not later when
it's actually needed.
"""

import os
import uuid


def check_path_writable(folder_path: str) -> tuple[bool, str]:
    """
    Args:
        folder_path: The folder to test.

    Returns:
        A (writable, error_message) tuple. error_message is empty if
        the folder is genuinely writable.
    """
    if not os.path.isdir(folder_path):
        return False, f"This location doesn't exist or isn't a folder:\n\n{folder_path}"

    test_file_path = os.path.join(folder_path, f".er-servicedesk-write-test-{uuid.uuid4().hex}.tmp")
    try:
        with open(test_file_path, "wb") as f:
            f.write(b"write test")
    except OSError as e:
        return False, f"This location exists, but isn't writable:\n\n{e}"
    finally:
        try:
            os.remove(test_file_path)
        except OSError:
            # Non-fatal -- the write itself already succeeded, which is
            # what actually matters here. A stray leftover test file
            # (extremely unlikely, since the write above just proved
            # this account CAN delete things it creates in almost every
            # real permission model) isn't worth failing the whole
            # check over.
            pass

    return True, ""
