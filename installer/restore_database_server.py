# ER-ServiceDesk/installer/restore_database_server.py
#
# Restores the SERVER database from a backup file. Same design as
# restore_database_local.py -- standalone, no login, no listener,
# machine access is the auth check (RDP access to this specific
# Server machine is already a meaningfully narrow, privileged
# credential, the same trust level Server Resources already leans
# on). See that file's own header for the full reasoning.
#
# The one real difference from the Local version: this targets the
# VM's remote Docker daemon via DOCKER_HOST, not a local one -- the
# actual database lives inside the Hyper-V VM, not on this Windows
# host directly.
#
# Compiled to a standalone .exe for the same reason as the Local
# version -- avoids PowerShell's execution policy blocking an
# unsigned script from running at all.

import os
import subprocess
import sys
from datetime import datetime


def pick_file(title: str) -> str:
    """
    Shows a real native Windows file-open dialog instead of asking the
    admin to type/remember an exact path from memory -- especially
    important for a long network share path during an actual
    emergency. Falls back to a plain text prompt if the dialog itself
    can't be shown for any reason (e.g. a genuinely broken Tk/Tcl
    install), so this can never be the one thing blocking a restore.

    Args:
        title: Shown in the dialog's own title bar.

    Returns:
        The chosen path, or an empty string if cancelled.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askopenfilename(
            title=title,
            filetypes=[("Database backup files", "*.dump"), ("All files", "*.*")],
        )
        root.destroy()
        return path
    except Exception:
        return input(f"{title} (type the full path): ").strip()


def pick_folder(title: str) -> str:
    """
    Shows a real native Windows folder-browse dialog, same reasoning
    as pick_file(). Falls back to a plain text prompt if the dialog
    itself can't be shown for any reason.

    Args:
        title: Shown in the dialog's own title bar.

    Returns:
        The chosen folder path, or an empty string if cancelled/skipped.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        path = filedialog.askdirectory(title=title)
        root.destroy()
        return path
    except Exception:
        return input(f"{title} (type the full path, or press Enter to skip): ").strip()


def run(cmd: list[str], env: dict, capture_stderr_to: str | None = None) -> int:
    """
    Args:
        cmd: The command and its arguments.
        env: The environment to run it in.
        capture_stderr_to: If given, stderr is redirected to this file
            path instead of being merged with stdout, so a real error
            message can be shown without it getting lost or
            interleaved with normal output.

    Returns:
        The command's exit code.
    """
    if capture_stderr_to:
        with open(capture_stderr_to, "wb") as f:
            result = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=f)
    else:
        result = subprocess.run(cmd, env=env)
    return result.returncode


def read_stderr_file(path: str) -> str:
    """Reads back whatever a run() call's capture_stderr_to wrote, for showing a real error message."""
    try:
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def main() -> int:
    print()
    print("=== ER-ServiceDesk Server Database Restore ===")
    print()
    print("This will REPLACE the current database with the contents of a")
    print("backup file. Everything currently in the database will be lost")
    print("unless it's captured by the safety backup this tool attempts")
    print("first.")
    print()

    print("Opening a file picker -- choose the backup file to restore from...")
    backup_file_path = pick_file("Select the backup file to restore from")
    if not backup_file_path:
        print("No file selected -- nothing was changed.")
        return 0
    if not os.path.isfile(backup_file_path):
        print(f"That file doesn't exist: {backup_file_path}")
        return 1

    print()
    confirmation = input("Type YES (all capitals) to confirm you want to REPLACE the current database: ")
    if confirmation != "YES":
        print("Not confirmed -- nothing was changed.")
        return 0

    # Same PATH/DOCKER_HOST setup already established and proven
    # working elsewhere in this project for Server mode's own remote
    # docker-compose calls (migration_listener.ps1, server_backup_listener.ps1).
    install_dir = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ER-ServiceDesk")
    vm_install_dir = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ER-ServiceDesk-VM")
    env = os.environ.copy()
    env["PATH"] = env.get("PATH", "") + f";{vm_install_dir};{os.path.join(vm_install_dir, 'docker')}"
    env["DOCKER_HOST"] = "tcp://192.168.100.10:2375"

    temp_dir = os.environ.get("TEMP", ".")
    cmd_err_path = os.path.join(temp_dir, "restore_cmd_stderr.txt")

    # -------------------------------------------------------------------
    # Safety backup attempt -- best-effort, never blocks the real
    # restore. Prompted interactively, same reasoning as the Local
    # version -- no dependency on any Client-side saved location this
    # standalone tool has no way to reach anyway.
    # -------------------------------------------------------------------
    print()
    print("Opening a folder picker -- choose where to save a safety backup (or close the dialog to skip)...")
    safety_backup_folder = pick_folder("Choose a networked folder to save a safety backup to (Cancel to skip)")

    if safety_backup_folder:
        print("Attempting safety backup...")
        try:
            os.makedirs(safety_backup_folder, exist_ok=True)
            safety_filename = f"er-servicedesk-pre-restore-backup-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}.dump"
            safety_dump_path = os.path.join(safety_backup_folder, safety_filename)
            container_dump_path = "/tmp/er-servicedesk-pre-restore-safety.dump"

            dump_rc = run(
                ["docker-compose", "exec", "-T", "db", "pg_dump", "-U", "postgres", "-Fc", "-f", container_dump_path, "erservicedesk"],
                env, cmd_err_path,
            )
            cp_rc = -1
            if dump_rc == 0:
                cp_rc = run(
                    ["docker", "cp", f"er-servicedesk-app-postgres:{container_dump_path}", safety_dump_path],
                    env, cmd_err_path,
                )

            if dump_rc == 0 and cp_rc == 0 and os.path.isfile(safety_dump_path):
                print(f"Safety backup saved to: {safety_dump_path}")
            else:
                print("Safety backup could not be completed -- proceeding with the restore anyway.")
                print(read_stderr_file(cmd_err_path))
        except OSError as e:
            print(f"Safety backup failed: {e} -- proceeding with the restore anyway.")
    else:
        print("Skipping safety backup.")

    # -------------------------------------------------------------------
    # The actual restore.
    # -------------------------------------------------------------------
    print()
    print("Restoring database...")

    cp_rc = run(
        ["docker", "cp", backup_file_path, "er-servicedesk-app-postgres:/tmp/er-servicedesk-restore.dump"],
        env, cmd_err_path,
    )
    if cp_rc != 0:
        print("Failed to copy the backup file into the container:")
        print(read_stderr_file(cmd_err_path))
        return 1

    restore_rc = run(
        ["docker-compose", "exec", "-T", "db", "pg_restore", "-U", "postgres", "-d", "erservicedesk", "--clean", "--if-exists", "/tmp/er-servicedesk-restore.dump"],
        env, cmd_err_path,
    )
    if restore_rc != 0:
        print("Restore failed:")
        print(read_stderr_file(cmd_err_path))
        return 1

    print()
    print("Restore completed successfully.")
    return 0


if __name__ == "__main__":
    exit_code = main()
    input("\nPress Enter to close this window...")
    sys.exit(exit_code)
