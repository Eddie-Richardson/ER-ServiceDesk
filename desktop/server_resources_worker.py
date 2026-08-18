# ER-ServiceDesk/desktop/server_resources_worker.py

"""
Talks to the Server VM's resize listener (installer/vm_resize_listener.ps1)
on a background QThread, matching the same pattern every other
network-bound worker in this app already uses (BackendStartupWorker,
MigrateToServerWorker, DatabaseBackupWorker) so the GUI never freezes
while waiting on a request.

Authentication is real Windows credentials (validated server-side via
LogonUser -- the same mechanism RDP itself uses), sent as standard
HTTP Basic Auth. Deliberately not a bespoke token the way migration
uses one -- resizing the server later is functionally the same trust
level as an admin RDPing into that machine directly, so this reuses
that exact credential instead of adding another secret to keep track
of.
"""

import requests
from PySide6.QtCore import QObject, Signal


class ServerResourcesWorker(QObject):
    """
    Fetches current VM resource status, or applies a single resize
    action, against the Server's resize listener.

    Signals:
        finished(bool, str, object): Emitted exactly once. First
            argument is success/failure. Second is a message meant to
            be shown directly to the admin. Third is the parsed status
            dict for a "status" action, or None for every other action.
    """

    finished = Signal(bool, str, object)

    def __init__(self, server_host: str, username: str, password: str, action: str, **kwargs):
        """
        Args:
            server_host: The Server's bare hostname/IP, e.g. "192.168.1.50"
                (no scheme, no port -- this worker always targets port 8002).
            action: One of "status", "memory", "cpu", "disk".
            **kwargs: Action-specific value -- max_gb for "memory",
                count for "cpu", cap_gb for "disk". Unused for "status".
        """
        super().__init__()
        self.server_host = server_host
        self.username = username
        self.password = password
        self.action = action
        self.kwargs = kwargs

    def run(self):
        """Entry point when this worker is moved to a QThread and started."""
        base_url = f"http://{self.server_host}:8002/resources"
        auth = (self.username, self.password)

        try:
            if self.action == "status":
                response = requests.get(f"{base_url}/status", auth=auth, timeout=15)
            elif self.action == "memory":
                response = requests.post(f"{base_url}/memory", auth=auth, timeout=15, json={"max_gb": self.kwargs["max_gb"]})
            elif self.action == "cpu":
                # A real, if brief, VM restart happens server-side for
                # this one (Set-VMProcessor requires the VM to be off)
                # -- a longer timeout than the others, since the
                # request genuinely doesn't finish until the VM is
                # already back up.
                response = requests.post(f"{base_url}/cpu", auth=auth, timeout=60, json={"count": self.kwargs["count"]})
            elif self.action == "disk":
                # Includes growpart/resize2fs running inside the VM
                # over SSH before this returns -- generous timeout for
                # the same reason as "cpu" above.
                response = requests.post(f"{base_url}/disk", auth=auth, timeout=60, json={"cap_gb": self.kwargs["cap_gb"]})
            else:
                self.finished.emit(False, f"Unknown action: {self.action}", None)
                return
        except requests.exceptions.RequestException as e:
            self.finished.emit(False, f"Could not reach the server: {e}", None)
            return

        if response.status_code == 401:
            self.finished.emit(False, "Invalid username or password.", None)
            return

        try:
            payload = response.json()
        except ValueError:
            self.finished.emit(False, f"Server returned an unexpected response (status {response.status_code}).", None)
            return

        success = bool(payload.get("success"))
        message = payload.get("message", "")

        if self.action == "status" and success:
            self.finished.emit(True, message, payload)
        else:
            self.finished.emit(success, message, None)
