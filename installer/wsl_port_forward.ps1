# ER-ServiceDesk/installer/wsl_port_forward.ps1
#
# Bridges Windows' own network-facing interface to the WSL2 distro's
# internal address for port 8000 (the API) -- confirmed as a real,
# documented, fundamental WSL2 networking limitation, not a bug in
# anything else here: Docker containers running inside WSL2 are only
# reachable from the Windows host itself, via WSL2's own special
# localhost forwarding, never from another physical machine on the
# network, unless Windows is explicitly told to forward that traffic
# in. Confirmed by a real test: the migration listener (a plain
# PowerShell script running directly on Windows, never touching WSL2
# at all) was reachable from another machine the whole time; the API
# (inside a container, inside WSL2) was not, despite an identical,
# confirmed-correct firewall rule for its own port.
#
# Runs at every boot, not just once at install -- WSL2's internal IP
# address changes every time the distro restarts, confirmed via
# multiple real sources, so a rule set once during install would
# silently go stale after the very next reboot.
#
# Logging added after a real test showed no change at all with no way
# to tell why -- this script previously failed completely silently if
# it couldn't find the WSL2 IP yet, giving zero information about
# what actually happened. Written to a fixed location inside this
# script's own folder, not $env:TEMP -- already confirmed elsewhere
# tonight that $env:TEMP resolves differently for SYSTEM (the account
# this actually runs as, via the Scheduled Task) than for an
# interactive session.

$InstallDir = $PSScriptRoot
$LogPath = Join-Path $InstallDir "wsl_port_forward_log.txt"

function Write-Log {
    param([string]$Message)
    "$(Get-Date -Format o) - $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Write-Log "=== wsl_port_forward.ps1 STARTED ==="

$DistroName = "ER-ServiceDesk-Docker"
$Port = 8000

# Discover the distro's current internal IP -- never hardcoded, since
# it changes on every restart.
$WslIpRaw = & wsl -d $DistroName -u root -e hostname -I
Write-Log "Raw output from 'wsl -d $DistroName -u root -e hostname -I': $($WslIpRaw | Out-String)"

$WslIp = $WslIpRaw.Trim().Split(" ")[0]
Write-Log "Parsed WSL IP: '$WslIp'"

if ([string]::IsNullOrWhiteSpace($WslIp)) {
    # Distro isn't up yet, or hostname -I returned nothing -- nothing
    # real to forward to. Exiting quietly rather than adding a rule
    # pointing at an empty address; a later boot/retry will pick this
    # back up once the distro is actually running.
    Write-Log "WSL IP is empty -- exiting without creating a rule. This is why nothing would have changed."
    exit 1
}

# Remove any existing rule for this port first -- it may still be
# pointing at a now-stale IP from a previous boot.
Write-Log "Removing any existing portproxy rule for port $Port..."
& netsh interface portproxy delete v4tov4 listenport=$Port listenaddress=0.0.0.0 2>$null

Write-Log "Adding portproxy rule: 0.0.0.0:$Port -> ${WslIp}:$Port"
$AddResult = & netsh interface portproxy add v4tov4 listenport=$Port listenaddress=0.0.0.0 connectport=$Port connectaddress=$WslIp
Write-Log "netsh add result: $($AddResult | Out-String)"

Write-Log "Verifying the rule now exists:"
$ShowResult = & netsh interface portproxy show v4tov4
Write-Log "$($ShowResult | Out-String)"

Write-Log "=== wsl_port_forward.ps1 FINISHED ==="
