# ER-ServiceDesk/installer/server_backup_listener.ps1
#
# Persistent listener letting an admin trigger a database backup
# remotely from the desktop app's Settings -> Server Backup tab
# (Client mode only). Deliberately its own listener, separate from
# vm_resize_listener.ps1 -- each listener is scoped to one concern,
# not a shared "do several admin things" endpoint.
#
# The backup itself is created here (two-step pg_dump inside the
# container, then docker cp out), but the FILE never gets saved on the
# Server -- it's streamed back to the Client as the HTTP response
# body, and the CLIENT is what writes it to the admin-configured
# networked location. This is deliberate: the Server's own listener
# runs as SYSTEM, which has no network identity of its own to
# authenticate against a network share with. The admin's own
# already-logged-in Windows session already has legitimate network
# access -- reusing that avoids needing to store a second set of
# network credentials anywhere on the Server just for this.
#
# Authentication is real Windows credentials via LogonUser (the same
# mechanism RDP itself is built on), not a bespoke token -- same
# reasoning and same pattern as vm_resize_listener.ps1.
#
# Security note, same as every other listener in this project: plain
# HTTP, no TLS, so the Windows password travels in cleartext on the
# local network during each request. Acceptable for a local-network
# admin action between machines the shop already controls.

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $InstallDir "server_backup_listener_log.txt"
$ListenPort = 8003

$script:LastLogTime = Get-Date
function Write-Log {
    param([string]$Message)
    $Now = Get-Date
    $SinceLast = [math]::Round(($Now - $script:LastLogTime).TotalSeconds, 1)
    $script:LastLogTime = $Now
    "$($Now.ToString('o')) - [+${SinceLast}s] $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Overwrite, not append -- same reasoning as the other listeners.
Remove-Item -Path $LogPath -Force -ErrorAction SilentlyContinue
Write-Log "=== server_backup_listener.ps1 STARTED ==="

# Same fix already proven necessary in migration_listener.ps1 -- this
# runs as a Scheduled Task under SYSTEM, whose environment was already
# established before this installer's own setx /M PATH/DOCKER_HOST
# calls ran, so it never inherits those changes the way a genuinely
# new login session would. Setting both explicitly here rather than
# depending on inheritance at all.
$VMInstallDir = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-VM"
$env:PATH = $env:PATH + ";$VMInstallDir;$VMInstallDir\docker"
$env:DOCKER_HOST = "tcp://192.168.100.10:2375"

# ---------------------------------------------------------------------------
# Windows credential validation via LogonUser -- identical to
# vm_resize_listener.ps1's own implementation. See that file for the
# full reasoning on why this is used instead of a bespoke token.
# ---------------------------------------------------------------------------
Add-Type -Namespace ErServiceDeskAuth -Name NativeMethods -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("advapi32.dll", SetLastError = true)]
public static extern bool LogonUser(string lpszUsername, string lpszDomain, string lpszPassword, int dwLogonType, int dwLogonProvider, out System.IntPtr phToken);
[System.Runtime.InteropServices.DllImport("kernel32.dll", CharSet = System.Runtime.InteropServices.CharSet.Auto)]
public static extern bool CloseHandle(System.IntPtr handle);
"@

function Test-WindowsCredential {
    param([string]$Username, [string]$Password)
    $LOGON32_LOGON_NETWORK = 3
    $LOGON32_PROVIDER_DEFAULT = 0
    $tokenHandle = [IntPtr]::Zero
    try {
        $ok = [ErServiceDeskAuth.NativeMethods]::LogonUser($Username, ".", $Password, $LOGON32_LOGON_NETWORK, $LOGON32_PROVIDER_DEFAULT, [ref]$tokenHandle)
        return [bool]$ok
    }
    finally {
        if ($tokenHandle -ne [IntPtr]::Zero) {
            [ErServiceDeskAuth.NativeMethods]::CloseHandle($tokenHandle) | Out-Null
        }
    }
}

function Get-BasicAuthCredential {
    param($Request)
    $AuthHeader = $Request.Headers["Authorization"]
    if (-not $AuthHeader -or -not $AuthHeader.StartsWith("Basic ")) {
        return $null
    }
    try {
        $Decoded = [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($AuthHeader.Substring(6)))
        $Parts = $Decoded.Split(":", 2)
        if ($Parts.Length -ne 2) { return $null }
        return @{ Username = $Parts[0]; Password = $Parts[1] }
    }
    catch {
        return $null
    }
}

$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://+:$ListenPort/backup/")

# Same outer retry loop as vm_resize_listener.ps1 -- this listener has
# no natural end either, an admin might back up any number of times,
# so an unexpected failure reopens the listener instead of letting the
# whole process quietly die with nothing left running until reboot.
while ($true) {
    try {
        $Listener.Start()
        Write-Log "Listening on port $ListenPort..."

        while ($Listener.IsListening) {
            $Context = $Listener.GetContext()
            $Request = $Context.Request
            $Response = $Context.Response

            try {
                $Cred = Get-BasicAuthCredential -Request $Request
                if (-not $Cred -or -not (Test-WindowsCredential -Username $Cred.Username -Password $Cred.Password)) {
                    $Response.StatusCode = 401
                    $Response.Close()
                    continue
                }

                if ($Request.HttpMethod -ne "GET" -or $Request.Url.AbsolutePath -ne "/backup/create") {
                    $Response.StatusCode = 404
                    $Response.Close()
                    continue
                }

                Write-Log "Authenticated backup request from $($Cred.Username)."

                $ContainerDumpPath = "/tmp/er-servicedesk-server-backup.dump"
                $LocalDumpPath = Join-Path $InstallDir "server_backup_temp.dump"
                $CmdErrPath = Join-Path $InstallDir "server_backup_cmd_stderr.txt"

                # Same $ErrorActionPreference relaxation already proven
                # necessary in migration_listener.ps1 -- PowerShell can
                # auto-convert these native commands' stderr into a
                # terminating exception under $ErrorActionPreference =
                # "Stop", even redirected to a file, which would skip
                # right past our own explicit exit-code checks below.
                $PreviousErrorActionPreference = $ErrorActionPreference
                $ErrorActionPreference = "Continue"

                Push-Location $InstallDir
                $Success = $true
                $ErrorMessage = ""

                & docker-compose exec -T db pg_dump -U postgres -Fc -f $ContainerDumpPath erservicedesk 2> $CmdErrPath
                if ($LASTEXITCODE -ne 0) {
                    $Success = $false
                    $ErrorMessage = "pg_dump failed: $(Get-Content $CmdErrPath -Raw)"
                }

                if ($Success) {
                    & docker cp "er-servicedesk-app-postgres:${ContainerDumpPath}" $LocalDumpPath 2> $CmdErrPath
                    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $LocalDumpPath)) {
                        $Success = $false
                        $ErrorMessage = "docker cp failed: $(Get-Content $CmdErrPath -Raw)"
                    }
                }

                # Best-effort cleanup of the dump file left inside the
                # container -- not critical if this itself fails (a
                # leftover temp file inside the container is harmless
                # and gets overwritten by -f on the next run), so
                # errors here are logged but never block the response.
                & docker-compose exec -T db rm -f $ContainerDumpPath 2> $CmdErrPath
                if ($LASTEXITCODE -ne 0) {
                    Write-Log "Non-fatal: could not clean up $ContainerDumpPath inside the container: $(Get-Content $CmdErrPath -Raw)"
                }

                Pop-Location
                $ErrorActionPreference = $PreviousErrorActionPreference

                if (-not $Success) {
                    Write-Log "Backup failed: $ErrorMessage"
                    $Response.StatusCode = 500
                    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($ErrorMessage)
                    $Response.ContentType = "text/plain"
                    $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
                    $Response.Close()
                    continue
                }

                $DumpBytes = [System.IO.File]::ReadAllBytes($LocalDumpPath)
                Remove-Item -Path $LocalDumpPath -Force -ErrorAction SilentlyContinue

                Write-Log "Backup succeeded ($($DumpBytes.Length) bytes), sending to client."
                $Response.StatusCode = 200
                $Response.ContentType = "application/octet-stream"
                $Response.ContentLength64 = $DumpBytes.Length
                $Response.OutputStream.Write($DumpBytes, 0, $DumpBytes.Length)
                $Response.Close()
            }
            catch {
                Write-Log "Request handling error: $_"
                try {
                    $Response.StatusCode = 500
                    $Response.Close()
                }
                catch {
                    # Response may already be closed/broken -- nothing
                    # further to do for this one request.
                }
            }
        }
    }
    catch {
        Write-Log "Listener-level error, reopening in 10 seconds: $_"
        try { $Listener.Stop() } catch {}
        Start-Sleep -Seconds 10
    }
}
