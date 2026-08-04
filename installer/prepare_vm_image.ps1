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

function Write-Log {
    param([string]$Message)
    "$(Get-Date -Format o) - $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Write-Log "=== prepare_vm_image.ps1 STARTED ==="

if (Test-Path $MasterVhdxPath) {
    Write-Log "Master VHDX already exists at $MasterVhdxPath -- nothing to do."
    exit 0
}

New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

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
        Invoke-WebRequest -Uri $QcowUrl -OutFile $QcowPath -UseBasicParsing
        Write-Log "Downloaded to $QcowPath"
    }
    else {
        Write-Log "Ubuntu cloud image already downloaded, skipping."
    }

    if (-not (Test-Path $QemuImgExe)) {
        Write-Log "Downloading qemu-img-windows-x64..."
        Invoke-WebRequest -Uri $QemuImgZipUrl -OutFile $QemuImgZipPath -UseBasicParsing
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

Write-Log "=== prepare_vm_image.ps1 FINISHED ==="
exit 0
