# ER-ServiceDesk/installer/server_startup.ps1
#
# Consolidated boot-time startup script -- replaces THREE separate,
# unordered Scheduled Tasks (WSL2/Docker keep-alive, port forwarding,
# .env self-healing) with ONE script that does everything in a
# guaranteed, strict order, waiting for each step to genuinely be
# ready before moving on to the next. Windows Task Scheduler has no
# real dependency mechanism between multiple "at startup" tasks -- a
# real test showed exactly the failure this causes: env_self_healing's
# own docker-compose up -d running before WSL2/Docker were actually
# ready, confirmed directly via a real "connection actively refused"
# error on docker ps, meaning Docker itself hadn't come up yet at all.
#
# Every step below waits and retries until it's genuinely ready,
# rather than firing once and hoping for the best.

$DistroName = "ER-ServiceDesk-Docker"
$InstallDir = $PSScriptRoot
$LogPath = Join-Path $InstallDir "server_startup_log.txt"

function Write-Log {
    param([string]$Message)
    "$(Get-Date -Format o) - $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Write-Log "=== server_startup.ps1 STARTED ==="

# STEP 1: Start the WSL2 distro and confirm it's genuinely responsive
# -- launching it doesn't guarantee it can accept further commands
# immediately afterward.
Write-Log "Step 1: Starting WSL2 distro and waiting for it to respond..."
Start-Process -FilePath "wsl.exe" -ArgumentList "-d $DistroName -u root -e sleep infinity" -WindowStyle Hidden

$distroReady = $false
for ($i = 0; $i -lt 30; $i++) {
    try {
        $result = & wsl -d $DistroName -u root -e echo ready 2>&1
        $wslExitCode = $LASTEXITCODE
        $resultType = if ($null -eq $result) { "(null)" } else { $result.GetType().Name }
        Write-Log "Attempt $($i + 1): raw result = $($result | Out-String) | type = $resultType | LASTEXITCODE = $wslExitCode"
    }
    catch {
        Write-Log "Attempt $($i + 1): EXCEPTION calling wsl.exe -- $($_.Exception.GetType().FullName): $($_.Exception.Message)"
        $result = $null
    }
    if ($result -eq "ready") {
        $distroReady = $true
        Write-Log "Distro responded after $($i + 1) attempt(s)."
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $distroReady) {
    Write-Log "Distro never became responsive after 30 attempts (60 seconds). Stopping here."
    exit 1
}

# STEP 2: Wait for the Docker daemon itself to respond -- the distro
# being up doesn't mean dockerd has finished starting yet. Checked
# from inside the distro directly (not via the Windows-side
# DOCKER_HOST/TCP path), since the port-forward rule hasn't been set
# up yet at this point in the sequence.
Write-Log "Step 2: Waiting for Docker daemon to respond..."
$dockerReady = $false
for ($i = 0; $i -lt 30; $i++) {
    $dockerResult = & wsl -d $DistroName -u root -e docker version 2>&1
    Write-Log "Attempt $($i + 1): LASTEXITCODE = $LASTEXITCODE, output = $($dockerResult | Out-String)"
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        Write-Log "Docker daemon responded after $($i + 1) attempt(s)."
        break
    }
    Start-Sleep -Seconds 2
}

if (-not $dockerReady) {
    Write-Log "Docker daemon never became responsive after 30 attempts (60 seconds). Stopping here."
    exit 1
}

# STEP 3: Set up the port-forward rule -- needs the distro's internal
# IP address, which requires it to genuinely be up first (confirmed by
# Steps 1-2 above). WSL2's internal IP changes every restart, so this
# has to run fresh at every boot, never a value saved from before.
Write-Log "Step 3: Setting up port forwarding..."
$Port = 8000
$WslIpRaw = & wsl -d $DistroName -u root -e hostname -I
$WslIp = $WslIpRaw.Trim().Split(" ")[0]
Write-Log "WSL IP: '$WslIp'"

if ([string]::IsNullOrWhiteSpace($WslIp)) {
    Write-Log "WSL IP is empty -- cannot set up port forwarding this time. Continuing anyway; containers may still start correctly, just not be reachable from other machines until this is retried."
}
else {
    & netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=0.0.0.0 2>$null
    $AddResult = & netsh interface portproxy add v4tov4 listenport=$Port listenaddress=0.0.0.0 connectport=$Port connectaddress=$WslIp
    Write-Log "netsh add result: $($AddResult | Out-String)"
}

# STEP 4: .env self-healing -- restore from backup if the main copy is
# missing. Same recovery logic desktop/env_recovery.py already
# provides for Local/Client.
Write-Log "Step 4: Checking .env..."
$EnvPath = Join-Path $InstallDir ".env"
$BackupEnvPath = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-Backup\.env"

if (-not (Test-Path $EnvPath)) {
    if (Test-Path $BackupEnvPath) {
        Copy-Item -Path $BackupEnvPath -Destination $EnvPath -Force
        Write-Log ".env was missing, restored from backup."
    }
    else {
        Write-Log ".env is missing from both the main install location and the backup folder. Cannot start containers without it."
        try {
            New-EventLog -LogName Application -Source "ER-ServiceDesk" -ErrorAction SilentlyContinue
            Write-EventLog -LogName Application -Source "ER-ServiceDesk" -EventId 1 -EntryType Error `
                -Message ".env is missing from both the main install location and the backup folder. ER-ServiceDesk cannot start until it's restored. Do NOT reinstall -- that will erase existing data."
        }
        catch {
            # Even logging to the Event Log failed -- nothing further
            # to do here.
        }
        exit 1
    }
}
else {
    Write-Log ".env is present, nothing to restore."
}

# STEP 5: Bring the containers up. Genuinely necessary, not redundant
# with docker-compose.yml's own restart: unless-stopped policy -- that
# only handles already-existing containers coming back automatically
# when Docker restarts; it re-reads nothing from .env, and has nothing
# to restart at all if the containers were never created in the first
# place.
Write-Log "Step 5: Starting containers..."
$WSLInstallDir = Join-Path (Split-Path -Parent $InstallDir) "ER-ServiceDesk-WSL"
$env:PATH = $env:PATH + ";$WSLInstallDir;$WSLInstallDir\docker"
$env:DOCKER_HOST = "tcp://[::1]:2375"

Push-Location $InstallDir
try {
    $UpResult = & docker-compose up -d 2>&1
    Write-Log "docker-compose up -d result: $($UpResult | Out-String)"
}
finally {
    Pop-Location
}

Write-Log "=== server_startup.ps1 FINISHED ==="
