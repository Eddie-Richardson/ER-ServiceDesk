# ER-ServiceDesk/installer/migration_listener.ps1
#
# Standalone Windows-side listener for a Migration Target server,
# receiving a real Local-to-Server migration -- and this file exists
# specifically because of a real design flaw caught before it became
# a real bug: the original plan had the server's own FastAPI backend
# (running inside the api Docker container) receive the migration and
# recreate its own containers to pick up the new .env. That's a
# genuine paradox -- code running inside a container can't tear down
# and recreate the very container it's running in and still finish
# responding to the request that told it to. This script runs
# directly on the Windows host, outside Docker entirely, so it never
# hits that problem: it can freely stop, reconfigure, and restart the
# containers because it was never one of them.
#
# This is plain PowerShell, not Python, for the same reason the
# .env self-healing task (a separate, still-unbuilt piece) has to be:
# Server has no bundled Python interpreter to rely on at all -- no exe
# is ever installed there.
#
# Launched once, detached, at the end of Migration Target's install
# (see setup.iss), and re-launched on every boot via a Scheduled Task
# in case a reboot happens before the real migration arrives. Runs in
# a loop accepting connections, but exits entirely after one
# successfully completed migration -- there's no reason to keep an
# authenticated listener running once its one job is done, and
# leaving one running indefinitely afterward would just be
# unnecessary exposed surface for no remaining benefit.
#
# Security note, worth being upfront about rather than glossing over:
# this listens over plain HTTP, authenticated only by the migration
# token already written to .env during install -- no TLS. Acceptable
# for a local-network migration between two machines an admin already
# controls, same class of tradeoff as the plaintext RunOnce password
# already accepted elsewhere in this installer -- not something to
# pretend is more secure than it is.

$ErrorActionPreference = "Stop"

$InstallDir = $PSScriptRoot

# Confirmed via a real migration failure: this file had NO logging at
# all before this, unlike create_server_vm.ps1 and the other VM
# scripts -- a genuine pg_restore failure surfaced to the client as
# nothing but a generic "pg_restore failed" message, with zero way to
# see the actual underlying error. Same Write-Log pattern already
# established everywhere else in this project.
$LogPath = Join-Path $InstallDir "migration_listener_log.txt"

# Overwrite, not append -- each run's log should only ever contain
# THAT run, not accumulate across every run this install has ever
# had.
Remove-Item -Path $LogPath -Force -ErrorAction SilentlyContinue

$script:LastLogTime = Get-Date
function Write-Log {
    param([string]$Message)
    $Now = Get-Date
    $SinceLast = [math]::Round(($Now - $script:LastLogTime).TotalSeconds, 1)
    $script:LastLogTime = $Now
    "$($Now.ToString('o')) - [+${SinceLast}s] $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

# A real migration test proved this script's own docker/docker-compose
# calls below fail with "'docker' is not recognized" -- this runs as a
# Scheduled Task under the SYSTEM account, and SYSTEM's environment was
# already established before this installer's own setx /M PATH/
# DOCKER_HOST calls ran, so it never picks up those changes the same
# way a genuinely new login session would. Same root cause, same fix
# already proven working for RunDockerSetup's own docker-compose calls
# in setup.iss -- setting both explicitly here rather than depending on
# inheritance at all.
#
# DOCKER_HOST points at the Server VM's static IP now, not WSL2's
# loopback address -- Docker itself runs inside a dedicated Hyper-V VM
# under this architecture (see create_server_vm.ps1), not WSL2. Every
# docker/docker-compose call below is otherwise completely unchanged:
# docker cp, docker-compose exec, and pg_restore all work identically
# over a remote DOCKER_HOST -- this was the one thing that actually
# needed to change when Server mode moved off WSL2.
#
# The PATH fix above this needed the same update and initially missed
# it -- confirmed via a real migration failure showing the exact same
# "'docker' is not recognized" symptom this whole block was written to
# fix in the first place. docker.exe/docker-compose.exe live under
# ER-ServiceDesk-VM now (see InstallDockerCLIOnWindows in setup.iss),
# not the old ER-ServiceDesk-WSL folder name -- DOCKER_HOST got updated
# when Server moved off WSL2, but this PATH construction was missed.
$VMInstallDir = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-VM"
$env:PATH = $env:PATH + ";$VMInstallDir;$VMInstallDir\docker"
$env:DOCKER_HOST = "tcp://192.168.100.10:2375"
$EnvPath = Join-Path $InstallDir ".env"
$ListenPort = 8001

function Read-EnvValue {
    <#
    .SYNOPSIS
    Reads a single KEY=value line's value out of the .env file already
    on disk -- used both to read the current MIGRATION_TOKEN (to
    validate incoming requests) and the current, bootstrap Postgres
    password (needed to authenticate the ALTER USER call that changes
    it to the real, incoming one).
    #>
    param([string]$Key)
    $line = Get-Content $EnvPath | Where-Object { $_ -like "$Key=*" } | Select-Object -First 1
    if (-not $line) { return $null }
    return $line.Substring($Key.Length + 1)
}

$MigrationToken = Read-EnvValue "MIGRATION_TOKEN"
if (-not $MigrationToken) {
    Write-Error "No MIGRATION_TOKEN found in .env -- this listener should only ever run on a Migration Target install. Exiting."
    exit 1
}

$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://+:$ListenPort/migrate/")
$Listener.Start()

while ($Listener.IsListening) {
    $Context = $Listener.GetContext()
    $Request = $Context.Request
    $Response = $Context.Response

    try {
        $ProvidedToken = $Request.Headers["X-Migration-Token"]

        if ($ProvidedToken -ne $MigrationToken) {
            $Response.StatusCode = 401
            $Body = [System.Text.Encoding]::UTF8.GetBytes("Invalid or missing migration token.")
            $Response.OutputStream.Write($Body, 0, $Body.Length)
            $Response.Close()
            continue
        }

        # The request body is the raw pg_dump binary data, and nothing
        # else -- deliberately not multipart form data, to avoid
        # needing to implement multipart parsing from scratch in
        # plain PowerShell. The real .env values travel as separate
        # HTTP headers instead, since they're all short strings.
        #
        # Written directly inside the install folder, not $env:TEMP --
        # a real check confirmed $env:TEMP resolves completely
        # differently for SYSTEM (the account this script actually
        # runs as, via the Scheduled Task) than for an interactive
        # session, meaning every manual check of the file so far was
        # looking at the wrong, unrelated location entirely. This
        # fixed, unambiguous path also means it's always findable at
        # the same place for any future troubleshooting, regardless of
        # which account context is running the script.
        $DumpPath = Join-Path $InstallDir "migration_upload.dump"
        $FileStream = [System.IO.File]::Create($DumpPath)
        $Request.InputStream.CopyTo($FileStream)
        $FileStream.Close()

        $NewSecretKey = $Request.Headers["X-Secret-Key"]
        $NewDeviceAccountEncryptionKey = $Request.Headers["X-Device-Account-Encryption-Key"]
        $NewPostgresPassword = $Request.Headers["X-Postgres-Password"]
        # Business name, email credentials, and SMTP/IMAP settings are
        # NOT carried this way anymore -- those are real database rows
        # now, so the migrated database dump itself already carries
        # them over correctly. No .env involvement for those at all.

        # The CURRENT (bootstrap) password is needed to authenticate
        # the ALTER USER call -- you have to already be connected to
        # change a password, the exact same reasoning already worked
        # through earlier for this project's Migrate to Server design.
        $CurrentPostgresPassword = Read-EnvValue "POSTGRES_PASSWORD"

        Push-Location $InstallDir
        $CmdErrPath = Join-Path $InstallDir "migration_cmd_stderr.txt"
        try {
            # Confirmed via a real migration failure: the outer catch
            # block's own caught exception message was DOCKER'S OWN
            # stderr text verbatim ("Successfully copied 0B..."), not
            # either of the fixed strings this code actually throws --
            # meaning something was auto-throwing BEFORE our own
            # explicit $LASTEXITCODE checks below ever got a chance to
            # run. Same category of bug already found and fixed once
            # for the SSH retry loop in create_server_vm.ps1:
            # PowerShell can auto-convert a native command's stderr
            # output into a terminating exception under
            # $ErrorActionPreference = "Stop", even when that stderr
            # is redirected to a file rather than merged via 2>&1.
            # Temporarily relaxing it to "Continue" around each
            # external call below prevents that auto-throw while still
            # allowing our OWN explicit $LASTEXITCODE checks to control
            # real pass/fail -- restored immediately after each call so
            # nothing else in this script loses the Stop behavior it
            # otherwise relies on.
            $PreviousErrorActionPreference = $ErrorActionPreference
            $ErrorActionPreference = "Continue"

            & docker cp $DumpPath "er-servicedesk-app-postgres:/tmp/migration.dump" 2> $CmdErrPath
            if ($LASTEXITCODE -ne 0) {
                $ErrorActionPreference = $PreviousErrorActionPreference
                Write-Log "docker cp failed: $(Get-Content $CmdErrPath -Raw)"
                throw "docker cp failed"
            }

            & docker-compose exec -T db pg_restore -U postgres -d erservicedesk --clean --if-exists /tmp/migration.dump 2> $CmdErrPath
            if ($LASTEXITCODE -ne 0) {
                $ErrorActionPreference = $PreviousErrorActionPreference
                Write-Log "pg_restore failed: $(Get-Content $CmdErrPath -Raw)"
                throw "pg_restore failed"
            }

            & docker-compose exec -T db psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$NewPostgresPassword';" 2> $CmdErrPath
            if ($LASTEXITCODE -ne 0) {
                $ErrorActionPreference = $PreviousErrorActionPreference
                Write-Log "ALTER USER failed: $(Get-Content $CmdErrPath -Raw)"
                throw "ALTER USER failed"
            }

            $ErrorActionPreference = $PreviousErrorActionPreference

            $NewEnvContent = @"
DATABASE_URL=postgresql+psycopg2://postgres:$NewPostgresPassword@db:5432/erservicedesk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$NewPostgresPassword
POSTGRES_DB=erservicedesk
SECRET_KEY=$NewSecretKey
DEVICE_ACCOUNT_ENCRYPTION_KEY=$NewDeviceAccountEncryptionKey
"@
            Set-Content -Path $EnvPath -Value $NewEnvContent -NoNewline

            $BackupEnvPath = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-Backup\.env"
            Set-Content -Path $BackupEnvPath -Value $NewEnvContent -NoNewline

            # Recreates the containers so the new .env actually takes
            # effect -- a plain restart doesn't re-read .env, only
            # container recreation does, the same lesson already
            # learned the hard way earlier in this project. Same
            # ErrorActionPreference/stderr-capture protection as the
            # three calls above -- this one had none at all before,
            # despite being just as capable of hitting the same bug.
            $ErrorActionPreference = "Continue"
            & docker-compose up -d --force-recreate 2> $CmdErrPath
            $RecreateExitCode = $LASTEXITCODE
            $ErrorActionPreference = $PreviousErrorActionPreference
            if ($RecreateExitCode -ne 0) {
                Write-Log "Container recreation failed: $(Get-Content $CmdErrPath -Raw)"
                throw "Container recreation failed"
            }

            $Response.StatusCode = 200
            $Body = [System.Text.Encoding]::UTF8.GetBytes("Migration completed successfully.")
            $Response.OutputStream.Write($Body, 0, $Body.Length)
            $Response.Close()

            Remove-Item $DumpPath -ErrorAction SilentlyContinue
            $Listener.Stop()
            break
        }
        finally {
            Pop-Location
        }
    }
    catch {
        $Response.StatusCode = 500
        $ErrorBody = [System.Text.Encoding]::UTF8.GetBytes("Migration failed: $_")
        $Response.OutputStream.Write($ErrorBody, 0, $ErrorBody.Length)
        $Response.Close()
        # A failed attempt does NOT stop the listener -- the admin may
        # retry once whatever caused the failure is fixed.
    }
}
