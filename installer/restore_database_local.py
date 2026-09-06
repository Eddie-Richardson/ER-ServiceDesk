# ER-ServiceDesk/installer/restore_database_local.py
"""
Restores the LOCAL database from a backup file. Deliberately a
standalone tool, not a desktop app feature -- a broken/corrupted
database is often exactly why the app can't even reach its login
screen in the first place, so gating restore behind a login that
might itself be unreachable would defeat the whole point. Run
directly on this machine, by someone who's already logged into
Windows here -- that access IS the authentication check, the same
trust level this whole app's Local design already rests on (anyone
who can log into this PC is already fully trusted, matching Local's
own single-shop-owner-PC assumption).

Compiled to a standalone .exe (see build_restore_exes.ps1) rather
than shipped as a raw .ps1 -- PowerShell's default execution policy
blocks an unsigned script from running at all, which is a genuinely
bad thing to put between a stressed admin and fixing a broken
database in an actual emergency. A double-clickable exe has no such
friction.

Genuinely destructive -- this REPLACES the current database
entirely. A real confirmation step (typing the word "YES", not just
a Y/N prompt) is required before anything happens. An automatic
safety backup of whatever's currently there is attempted first, but
never blocks the actual restore if it fails -- a failed safety
backup just confirms there was nothing to protect in the first
place (e.g. the database being restored TO is itself the reason
this is happening: fully corrupted or gone).
"""

import os
import subprocess
import sys
from datetime import datetime


def default_backup_folder() -> str:
    """
    Returns the same default location the main app's Database Backup
    tab uses (see desktop/database_backup_tab.py's own
    DEFAULT_BACKUP_FOLDER) -- so the restore tool's own file picker
    opens where a backup is actually likely to be, instead of falling
    back to Windows' own generic default (Documents) with no
    initialdir ever specified. Computed independently here rather than
    imported, since this standalone tool has no dependency on the
    desktop/ package (which pulls in PySide6, unneeded for a minimal,
    stdlib-only tool).

    Uses sys.executable (this exe's own real location) rather than
    os.getcwd(), unlike this file's own docker-compose calls
    elsewhere, which implicitly assume they're already running from
    the app's install folder -- reliable regardless of how this tool
    actually gets launched (double-click, a shortcut with a different
    "Start in" folder, or a command prompt cd'd somewhere else first).
    """
    app_dir = os.path.dirname(sys.executable)
    program_files_dir = os.path.dirname(app_dir)
    return os.path.join(program_files_dir, "ER-ServiceDesk-Backup", "Database-Backups")


def pick_file(title: str, initial_dir: str = "") -> str:
    """
    Shows a real native Windows file-open dialog instead of asking the
    admin to type/remember an exact path from memory -- especially
    important for a long network share path during an actual
    emergency. Falls back to a plain text prompt if the dialog itself
    can't be shown for any reason (e.g. a genuinely broken Tk/Tcl
    install), so this can never be the one thing blocking a restore.

    Args:
        title: Shown in the dialog's own title bar.
        initial_dir: Folder the dialog opens to. Without this, Tk
            falls back to Windows' own generic default (Documents),
            not necessarily where a backup actually is.

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
            initialdir=initial_dir,
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
    print("=== ER-ServiceDesk Local Database Restore ===")
    print()
    print("This will REPLACE the current database with the contents of a")
    print("backup file. Everything currently in the database will be lost")
    print("unless it's captured by the safety backup this tool attempts")
    print("first.")
    print()

    print("Opening a file picker -- choose the backup file to restore from...")
    backup_file_path = pick_file("Select the backup file to restore from", default_backup_folder())
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
    # working elsewhere in this project for Local mode's own
    # docker-compose calls.
    install_dir = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ER-ServiceDesk")
    wsl_install_dir = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "ER-ServiceDesk-WSL")
    env = os.environ.copy()
    env["PATH"] = env.get("PATH", "") + f";{wsl_install_dir};{os.path.join(wsl_install_dir, 'docker')}"
    env["DOCKER_HOST"] = "tcp://[::1]:2375"

    temp_dir = os.environ.get("TEMP", ".")
    cmd_err_path = os.path.join(temp_dir, "restore_cmd_stderr.txt")

    # -------------------------------------------------------------------
    # Safety backup attempt -- best-effort, never blocks the real
    # restore. Prompted interactively rather than reading a saved
    # location from anywhere, deliberately: this tool has to work
    # standalone, with no dependency on any GUI/QSettings value that
    # might not even be reachable in whatever state prompted needing
    # it in the first place.
    # -------------------------------------------------------------------
    print()
    print("Opening a folder picker -- choose where to save a safety backup (or close the dialog to skip)...")
    safety_backup_folder = pick_folder("Choose a folder to save a safety backup to (Cancel to skip)")

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

    # -------------------------------------------------------------------
    # Device user account password re-encryption -- best-effort, never
    # undoes the already-successful restore above. Looks for a
    # companion .key file next to the chosen .dump (written by
    # database_backup_worker.py at backup time, holding whatever
    # DEVICE_ACCOUNT_ENCRYPTION_KEY that machine had). Without it, any
    # device user account passwords in the restored database stay
    # encrypted with the OLD machine's key -- unreadable on this one --
    # since this machine's own, freshly-generated key won't match.
    # -------------------------------------------------------------------
    key_file_path = os.path.splitext(backup_file_path)[0] + ".key"
    if os.path.isfile(key_file_path):
        print()
        print("Found a matching encryption key file -- re-encrypting device user account passwords for this machine...")
        with open(key_file_path, "r") as f:
            old_key = f.read().strip()

        reencrypt_rc = run(
            ["docker-compose", "exec", "-T", "api", "python", "-m", "app.db.re_encrypt_device_passwords", old_key],
            env, cmd_err_path,
        )
        if reencrypt_rc == 0:
            print("Device user account passwords re-encrypted successfully.")
        else:
            print("Could not re-encrypt device user account passwords -- the rest of the restore is still successful, but any stored device account passwords may not be readable:")
            print(read_stderr_file(cmd_err_path))
    else:
        print()
        print("No matching .key file found alongside the backup -- if this backup came from a different machine and has any device user account passwords stored, they may not be readable here.")

    return 0


if __name__ == "__main__":
    exit_code = main()
    input("\nPress Enter to close this window...")
    sys.exit(exit_code)
