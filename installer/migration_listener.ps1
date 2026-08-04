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

# A real migration test proved this script's own docker/docker-compose
# calls below fail with "'docker' is not recognized" -- this runs as a
# Scheduled Task under the SYSTEM account, and SYSTEM's environment was
# already established before this installer's own setx /M PATH/
# DOCKER_HOST calls ran, so it never picks up those changes the same
# way a genuinely new login session would. Same root cause, same fix
# already proven working for RunDockerSetup's own docker-compose calls
# in setup.iss -- setting both explicitly here rather than depending on
# inheritance at all.
$WSLInstallDir = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-WSL"
$env:PATH = $env:PATH + ";$WSLInstallDir;$WSLInstallDir\docker"
$env:DOCKER_HOST = "tcp://[::1]:2375"
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

        $NewGmailAddress = $Request.Headers["X-Gmail-Address"]
        $NewGmailPassword = $Request.Headers["X-Gmail-App-Password"]
        $NewBusinessName = $Request.Headers["X-Business-Name"]
        $NewSecretKey = $Request.Headers["X-Secret-Key"]
        $NewPostgresPassword = $Request.Headers["X-Postgres-Password"]

        # The CURRENT (bootstrap) password is needed to authenticate
        # the ALTER USER call -- you have to already be connected to
        # change a password, the exact same reasoning already worked
        # through earlier for this project's Migrate to Server design.
        $CurrentPostgresPassword = Read-EnvValue "POSTGRES_PASSWORD"

        Push-Location $InstallDir
        try {
            & docker cp $DumpPath "er-servicedesk-app-postgres:/tmp/migration.dump"
            if ($LASTEXITCODE -ne 0) { throw "docker cp failed" }

            & docker-compose exec -T db pg_restore -U postgres -d erservicedesk --clean --if-exists /tmp/migration.dump
            if ($LASTEXITCODE -ne 0) { throw "pg_restore failed" }

            & docker-compose exec -T db psql -U postgres -c "ALTER USER postgres WITH PASSWORD '$NewPostgresPassword';"
            if ($LASTEXITCODE -ne 0) { throw "ALTER USER failed" }

            $NewEnvContent = @"
DATABASE_URL=postgresql+psycopg2://postgres:$NewPostgresPassword@db:5432/erservicedesk
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$NewPostgresPassword
POSTGRES_DB=erservicedesk
SECRET_KEY=$NewSecretKey
GMAIL_ADDRESS=$NewGmailAddress
GMAIL_APP_PASSWORD=$NewGmailPassword
BUSINESS_NAME=$NewBusinessName
"@
            Set-Content -Path $EnvPath -Value $NewEnvContent -NoNewline

            $BackupEnvPath = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-Backup\.env"
            Set-Content -Path $BackupEnvPath -Value $NewEnvContent -NoNewline

            # Recreates the containers so the new .env actually takes
            # effect -- a plain restart doesn't re-read .env, only
            # container recreation does, the same lesson already
            # learned the hard way earlier in this project.
            & docker-compose up -d --force-recreate
            if ($LASTEXITCODE -ne 0) { throw "Container recreation failed" }

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
