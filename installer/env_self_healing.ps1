# ER-ServiceDesk/installer/env_self_healing.ps1
#
# Server's startup self-healing script -- checks and restores .env if
# it's gone missing, then brings the containers up. Runs via a
# Scheduled Task at every Windows startup (see setup.iss).
#
# Plain PowerShell, not Python, for the same reason
# migration_listener.ps1 already is: Server has no bundled Python
# interpreter to rely on at all -- no exe is ever installed there.
#
# Replicates the exact same recovery logic desktop/env_recovery.py
# already provides for Local/Client (confirmed against that file's
# real, current content before writing this): if .env exists at the
# main install location, nothing to restore; if it's missing there but
# present in the backup folder, copy it back; if it's missing from
# both, that's a real problem this script can't solve on its own and
# it stops rather than trying to start Docker with no config at all.
#
# Also explicitly runs docker-compose up -d afterward -- confirmed as
# genuinely necessary, not redundant with Docker's own restart policy:
# docker-compose.yml's services now have restart: unless-stopped
# (added alongside this script), which handles the common case of
# already-existing containers coming back up automatically when Docker
# itself restarts. But a Docker-native restart of an EXISTING
# container does not re-read .env at all -- only container recreation
# does, the same lesson already learned the hard way earlier in this
# project -- and restart: unless-stopped has nothing to restart at all
# if the containers were never created in the first place. Explicitly
# running docker-compose up -d here is what makes this script a real
# safety net for both of those cases, not just the .env file itself.

$InstallDir = $PSScriptRoot
$EnvPath = Join-Path $InstallDir ".env"
$BackupEnvPath = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-Backup\.env"

if (-not (Test-Path $EnvPath)) {
    if (Test-Path $BackupEnvPath) {
        Copy-Item -Path $BackupEnvPath -Destination $EnvPath -Force
    }
    else {
        # Missing from both locations -- nothing this script can do on
        # its own. Logging to the Windows Event Log rather than just
        # exiting silently, since nothing is watching a console output
        # here (this runs unattended, at boot, via a Scheduled Task).
        try {
            New-EventLog -LogName Application -Source "ER-ServiceDesk" -ErrorAction SilentlyContinue
            Write-EventLog -LogName Application -Source "ER-ServiceDesk" -EventId 1 -EntryType Error `
                -Message ".env is missing from both the main install location and the backup folder. ER-ServiceDesk cannot start until it's restored. Do NOT reinstall -- that will erase existing data."
        }
        catch {
            # Even logging failed -- nothing further to do here.
        }
        exit 1
    }
}

Push-Location $InstallDir
try {
    & docker-compose up -d
}
finally {
    Pop-Location
}
