# ER-ServiceDesk/installer/prepare_vm_image.ps1
#
# Downloads Ubuntu's official generic cloud image (qcow2) and converts
# it to a VHDX Hyper-V can actually boot -- this is the master image
# every Server VM this installer creates gets copied from, never run
# directly (see create_server_vm.ps1, which copies THIS file before
# resizing/attaching it to any real VM).
#
# Deliberately NOT Ubuntu's Azure-format VHD download (the obvious
# "already a VHD" option) -- confirmed via real research that Azure's
# image has its cloud-init hardcoded to the Azure datasource only, and
# will not accept a local NoCloud seed ISO at all. The generic qcow2
# image is datasource-agnostic and is the only one that works with a
# self-built seed ISO on local Hyper-V.
#
# Conversion needs qemu-img, which Windows doesn't ship and which this
# project deliberately avoids pulling in via WSL (Server no longer
# uses WSL at all under this architecture) or the full QEMU installer
# (massively more than this needs). fdcastel/qemu-img-windows-x64 is a
# real, minimal, standalone Windows build of just qemu-img -- pinned to
# a specific tagged release (v10.0.0), the same pinning discipline
# already used elsewhere in this installer (WSLRootfsUrl, the Docker
# CLI/Compose downloads) after a real, confirmed incident where an
# "always latest" URL silently broke when the underlying file was
# renamed.
#
# Idempotent -- skips the download/convert entirely if the master VHDX
# already exists from a previous install on this machine. Every Server
# install (New Setup and Migration Target alike) calls this before
# create_server_vm.ps1, so only the very first one on a given machine
# actually pays the download/convert cost.

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,

    [Parameter(Mandatory = $true)]
    [string]$MasterVhdxPath
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $InstallDir "prepare_vm_image_log.txt"

# PowerShell 5.1 often still defaults to TLS 1.0/1.1 for outbound
# HTTPS unless told otherwise -- both cloud-images.ubuntu.com and
# GitHub's release CDN require 1.2+, so without this,
# Invoke-WebRequest below can fail with "Could not create SSL/TLS
# secure channel" on an otherwise-correct machine.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# Directory must exist BEFORE the first Write-Log call below -- Out-File
# creates the FILE itself, but not missing parent directories. On a
# fresh machine this folder genuinely doesn't exist yet the first time
# this script ever runs, so this has to come first, not after.
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Confirmed via real research: Invoke-WebRequest buffers an entire
# download into memory before writing anything to disk at all, which
# causes severe slowdowns specifically for large files -- multiple
# independent, confirmed sources show 3x to 20x slower than
# System.Net.WebClient for files in the hundreds-of-MB to multi-GB
# range, exactly the size of the cloud image this script downloads.
# Directly measured on a real install: this single download was 20.6
# of this script's total 21.4 minutes.
#
# WebClient itself has no built-in timeout parameter the way
# Invoke-WebRequest's -TimeoutSec does -- this subclass is the
# standard, documented way to add one, needed to preserve this
# project's own hard-learned lesson: a real, confirmed incident where
# Setup sat silently hung for 4+ hours with no indication anything was
# wrong, which is why -TimeoutSec exists on every download in this
# project's installer already.
Add-Type @"
using System.Net;
public class TimeoutWebClient : WebClient {
    public int TimeoutMs = 1800000;
    protected override WebRequest GetWebRequest(System.Uri address) {
        WebRequest request = base.GetWebRequest(address);
        if (request != null) {
            request.Timeout = TimeoutMs;
        }
        return request;
    }
}
"@

function Get-FileFast {
    param(
        [string]$Uri,
        [string]$OutFile,
        [int]$TimeoutSec
    )
    $client = New-Object TimeoutWebClient
    $client.TimeoutMs = $TimeoutSec * 1000
    try {
        $client.DownloadFile($Uri, $OutFile)
    }
    finally {
        $client.Dispose()
    }
}

# Overwrite, not append -- same reasoning as create_server_vm.ps1.
Remove-Item -Path $LogPath -Force -ErrorAction SilentlyContinue

$script:LastLogTime = Get-Date
$script:ScriptStartTime = $script:LastLogTime
function Write-Log {
    param([string]$Message)
    $Now = Get-Date
    $SinceLast = [math]::Round(($Now - $script:LastLogTime).TotalSeconds, 1)
    $script:LastLogTime = $Now
    "$($Now.ToString('o')) - [+${SinceLast}s] $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Write-Log "=== prepare_vm_image.ps1 STARTED ==="

if (Test-Path $MasterVhdxPath) {
    Write-Log "Master VHDX already exists at $MasterVhdxPath -- nothing to do."
    exit 0
}

# Pinned to a specific Ubuntu release, not a "current"/"latest" alias
# -- the exact same reasoning already applied to WSLRootfsUrl in
# setup.iss: a URL that silently starts pointing somewhere different
# is worse than one that needs a deliberate version bump later.
$QcowUrl = "https://cloud-images.ubuntu.com/releases/24.04/release/ubuntu-24.04-server-cloudimg-amd64.img"
$QcowPath = Join-Path $InstallDir "ubuntu-24.04-server-cloudimg-amd64.img"

$QemuImgZipUrl = "https://github.com/fdcastel/qemu-img-windows-x64/releases/download/v10.0.0/qemu-img-windows-x64-v10.0.0.zip"
$QemuImgZipPath = Join-Path $InstallDir "qemu-img-windows-x64.zip"
$QemuImgDir = Join-Path $InstallDir "qemu-img"
$QemuImgExe = Join-Path $QemuImgDir "qemu-img.exe"

try {
    if (-not (Test-Path $QcowPath)) {
        Write-Log "Downloading Ubuntu 24.04 cloud image..."
        # -TimeoutSec added after a real, confirmed hang elsewhere in
        # this installer (Setup sat stuck for 4+ hours with no
        # indication anything was wrong) -- no download anywhere in
        # this project had a timeout before that. Generous bound here
        # since this is a large file (several hundred MB).
        Get-FileFast -Uri $QcowUrl -OutFile $QcowPath -TimeoutSec 1800
        Write-Log "Downloaded to $QcowPath"
    }
    else {
        Write-Log "Ubuntu cloud image already downloaded, skipping."
    }

    if (-not (Test-Path $QemuImgExe)) {
        Write-Log "Downloading qemu-img-windows-x64..."
        Get-FileFast -Uri $QemuImgZipUrl -OutFile $QemuImgZipPath -TimeoutSec 300
        Expand-Archive -Path $QemuImgZipPath -DestinationPath $QemuImgDir -Force
        Write-Log "Extracted qemu-img to $QemuImgDir"

        if (-not (Test-Path $QemuImgExe)) {
            # The zip's internal folder layout isn't fully confirmed
            # by research alone -- if qemu-img.exe isn't directly at
            # the expected path, search one level deeper rather than
            # fail outright, since a version bump could plausibly
            # change the archive's internal structure without
            # changing anything about how this script should behave.
            $Found = Get-ChildItem -Path $QemuImgDir -Filter "qemu-img.exe" -Recurse | Select-Object -First 1
            if ($Found) {
                $QemuImgExe = $Found.FullName
                Write-Log "qemu-img.exe found at nested path: $QemuImgExe"
            }
            else {
                Write-Log "qemu-img.exe not found anywhere under $QemuImgDir after extraction."
                exit 1
            }
        }
    }
    else {
        Write-Log "qemu-img already present, skipping download."
    }

    Write-Log "Converting qcow2 to VHDX (this can take a few minutes)..."
    & $QemuImgExe convert -f qcow2 -O vhdx "$QcowPath" "$MasterVhdxPath"
    if ($LASTEXITCODE -ne 0) {
        Write-Log "qemu-img convert failed with exit code $LASTEXITCODE"
        exit 1
    }

    if (-not (Test-Path $MasterVhdxPath)) {
        Write-Log "Conversion reported success but $MasterVhdxPath does not exist."
        exit 1
    }

    Write-Log "Master VHDX created successfully at $MasterVhdxPath"
}
catch {
    Write-Log "EXCEPTION: $($_.Exception.GetType().FullName): $($_.Exception.Message)"
    exit 1
}

Write-Log "=== prepare_vm_image.ps1 FINISHED (total runtime: $([math]::Round(((Get-Date) - $script:ScriptStartTime).TotalMinutes, 1)) minutes) ==="
exit 0
