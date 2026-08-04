# ER-ServiceDesk/installer/create_server_vm.ps1
#
# Replaces the whole WSL2/Docker-Engine chain for Server mode with a
# genuine, dedicated Hyper-V Linux VM -- see setup.iss's own header
# comment for the full reasoning (wsl.exe cannot run unattended with
# no interactive session present, a real, documented, still-open WSL
# limitation, confirmed via extensive real testing before this
# architecture was chosen).
#
# Called once per Server install (New Setup or Migration Target) from
# CreateServerVM in setup.iss, itself called from
# DetectAndInstallServerPrerequisites -- the direct structural
# equivalent of InstallDockerInWSL for the Local/WSL2 path. Idempotent:
# if a VM by this name already exists (a re-run, or Setup resuming
# after the mid-install reboot InitializeSetup/CreateRunOnceEntry
# already handle), this confirms it's running and waits for it to be
# reachable rather than trying to create it again.
#
# Resource sizing is deliberately NOT hardcoded -- this software runs
# on whatever hardware a given repair shop already owns, which could
# be almost anything. Every value below is computed as a percentage of
# this specific host's own actual resources, with a floor and ceiling
# so a very small or very large host both still get something
# reasonable. Memory additionally uses Hyper-V's own Dynamic Memory
# feature, which is a better fit than any fixed number this installer
# could pick -- it lets the VM's actual memory footprint grow and
# shrink at runtime based on genuine demand, not a one-time guess made
# during install.

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,

    [Parameter(Mandatory = $true)]
    [string]$VMName,

    [Parameter(Mandatory = $true)]
    [string]$SwitchName,

    [Parameter(Mandatory = $true)]
    [string]$HostIP,

    [Parameter(Mandatory = $true)]
    [string]$StaticIP,

    [Parameter(Mandatory = $true)]
    [string]$SubnetPrefixLength,

    [Parameter(Mandatory = $true)]
    [string]$NatSubnetCidr,

    [Parameter(Mandatory = $true)]
    [string]$MasterVhdxPath
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $InstallDir "create_server_vm_log.txt"

function Write-Log {
    param([string]$Message)
    "$(Get-Date -Format o) - $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

Write-Log "=== create_server_vm.ps1 STARTED (VMName=$VMName) ==="
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# ---------------------------------------------------------------------------
# STEP 1: Internal NAT switch -- gives the VM a private, static-IP
# network that Windows itself can reach and forward into, without
# exposing the VM directly on the shop's real LAN. Chosen specifically
# over an external/bridged switch so Client installs keep pointing at
# the SERVER MACHINE's own IP, exactly as they do today -- a bridged
# switch would have made the VM's own separate IP the thing Clients
# need to know instead, a real behavior change this avoids.
#
# Idempotent -- Get-VMSwitch/Get-NetNat checks first, since re-running
# this (a retry, or Setup resuming after a reboot) must not fail just
# because the switch/NAT from an earlier attempt already exists.
#
# Windows only supports ONE NetNat object per host, confirmed via
# real research -- the name check below specifically distinguishes
# "our own NAT already exists, nothing to do" from "a NAT with a
# different name already exists," which would be a genuine conflict
# worth failing loudly on rather than silently colliding with.
# ---------------------------------------------------------------------------
Write-Log "Step 1: Ensuring internal NAT switch and NetNat exist..."

$ExistingSwitch = Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue
if (-not $ExistingSwitch) {
    Write-Log "Creating internal switch '$SwitchName'..."
    New-VMSwitch -SwitchName $SwitchName -SwitchType Internal | Out-Null
}
else {
    Write-Log "Switch '$SwitchName' already exists."
}

$AdapterAlias = "vEthernet ($SwitchName)"
$ExistingIP = Get-NetIPAddress -InterfaceAlias $AdapterAlias -IPAddress $HostIP -ErrorAction SilentlyContinue
if (-not $ExistingIP) {
    Write-Log "Assigning host IP $HostIP to '$AdapterAlias'..."
    New-NetIPAddress -IPAddress $HostIP -PrefixLength $SubnetPrefixLength -InterfaceAlias $AdapterAlias | Out-Null
}
else {
    Write-Log "Host IP $HostIP already assigned to '$AdapterAlias'."
}

$ExistingNat = Get-NetNat -Name $SwitchName -ErrorAction SilentlyContinue
if (-not $ExistingNat) {
    $AnyOtherNat = Get-NetNat -ErrorAction SilentlyContinue
    if ($AnyOtherNat) {
        Write-Log "A NetNat object already exists under a DIFFERENT name ($($AnyOtherNat.Name)) -- Windows only supports one per host. Not creating a second. This needs manual resolution."
        exit 1
    }
    Write-Log "Creating NetNat '$SwitchName' for $NatSubnetCidr..."
    New-NetNat -Name $SwitchName -InternalIPInterfaceAddressPrefix $NatSubnetCidr | Out-Null
}
else {
    Write-Log "NetNat '$SwitchName' already exists."
}

$ExistingMapping = Get-NetNatStaticMapping -NatName $SwitchName -ErrorAction SilentlyContinue |
    Where-Object { $_.ExternalPort -eq 8000 }
if (-not $ExistingMapping) {
    Write-Log "Adding static mapping: host:8000 -> ${StaticIP}:8000..."
    Add-NetNatStaticMapping -NatName $SwitchName -Protocol TCP `
        -ExternalIPAddress "0.0.0.0/32" -ExternalPort 8000 `
        -InternalIPAddress $StaticIP -InternalPort 8000 | Out-Null
}
else {
    Write-Log "Static mapping for port 8000 already exists."
}

# Docker's own daemon port (2375) -- Windows-side scripts (RunDockerSetup,
# migration_listener.ps1) need to reach this directly via DOCKER_HOST,
# but only FROM this host itself, not from the network -- no mapping
# needed for 2375 at all, since Windows reaches it over the internal
# switch's own routing (HostIP <-> StaticIP), never through the NAT's
# external side. Only port 8000 (the API, needed by real Clients on
# the network) and eventually 8001 (migration, Migration Target only)
# need actual static mappings.

# ---------------------------------------------------------------------------
# STEP 2: If the VM already exists, this is a re-run or a resume after
# reboot -- don't recreate it, just make sure it's running and skip to
# waiting for it to be ready.
# ---------------------------------------------------------------------------
$ExistingVM = Get-VM -Name $VMName -ErrorAction SilentlyContinue
if ($ExistingVM) {
    Write-Log "VM '$VMName' already exists (State=$($ExistingVM.State)) -- skipping creation."
    if ($ExistingVM.State -ne "Running") {
        Write-Log "Starting existing VM..."
        Start-VM -Name $VMName
    }
}
else {
    # -----------------------------------------------------------------------
    # STEP 3: Compute this host's own resource sizing. Percentage-based
    # with a floor and ceiling, deliberately not a fixed number -- this
    # runs on whatever hardware a given repair shop happens to own.
    # -----------------------------------------------------------------------
    Write-Log "Step 3: Computing VM sizing from host resources..."

    $ComputerSystem = Get-CimInstance -ClassName Win32_ComputerSystem
    $HostRamGB = [math]::Round($ComputerSystem.TotalPhysicalMemory / 1GB, 1)
    $HostLogicalProcessors = $ComputerSystem.NumberOfLogicalProcessors

    $InstallDrive = (Get-Item $InstallDir).PSDrive.Name
    $Volume = Get-Volume -DriveLetter $InstallDrive -ErrorAction SilentlyContinue
    if ($Volume) {
        $FreeDiskGB = [math]::Round($Volume.SizeRemaining / 1GB, 1)
    }
    else {
        Write-Log "Could not determine free disk space for drive $InstallDrive -- defaulting to a conservative 100GB assumption."
        $FreeDiskGB = 100
    }

    Write-Log "Host resources: RAM=${HostRamGB}GB, LogicalProcessors=$HostLogicalProcessors, FreeDisk(on ${InstallDrive}:)=${FreeDiskGB}GB"

    function Clamp([double]$Value, [double]$Min, [double]$Max) {
        if ($Value -lt $Min) { return $Min }
        if ($Value -gt $Max) { return $Max }
        return $Value
    }

    # vCPU: a quarter of the host's logical processors, floor 2 (this
    # stack -- Postgres, Redis, FastAPI, one RQ worker -- genuinely
    # needs at least that much to be responsive), ceiling 8 (a repair
    # shop's ticket/inventory load has no realistic need for more, and
    # an unbounded share would let this VM starve everything else the
    # host is doing).
    $VCpuCount = [int](Clamp ([math]::Round($HostLogicalProcessors * 0.25)) 2 8)

    # Memory: Dynamic Memory handles the actual runtime footprint, so
    # these three numbers are really just reasonable bounds, not a
    # precise target. Startup and minimum are deliberately modest --
    # the VM grows into more as Docker/Postgres actually need it, per
    # Hyper-V's own Dynamic Memory ballooning. Maximum is capped at
    # half the host's RAM so this VM can never starve the host machine
    # itself of memory for everything else it's doing.
    $MemStartupGB = [int](Clamp ([math]::Round($HostRamGB * 0.20)) 1 4)
    $MemMinGB = 1
    $MemMaxGB = [int](Clamp ([math]::Round($HostRamGB * 0.50)) 2 8)

    # Disk: a repair shop's ticket/customer/inventory database is not
    # a genuinely large-data workload -- even a busy shop's data is
    # realistically megabytes to low gigabytes, not the kind of thing
    # that needs a large fixed allocation "just in case." This cap
    # governs the VHDX's maximum GROWABLE size (see Resize-VHD below,
    # and cloud-init's own growpart/resizefs, which expand the actual
    # filesystem to fill whatever this cap allows) -- Ubuntu's cloud
    # image ships as a dynamically-expanding VHDX, so disk space on
    # the HOST is only actually consumed as data is genuinely written
    # inside the VM, never reserved upfront. A generous cap here costs
    # nothing until real data actually approaches it.
    $DiskCapGB = [int](Clamp ([math]::Round($FreeDiskGB * 0.15)) 20 200)

    Write-Log "Computed sizing: vCPU=$VCpuCount, MemStartup=${MemStartupGB}GB, MemMin=${MemMinGB}GB, MemMax=${MemMaxGB}GB, DiskCap=${DiskCapGB}GB"

    # -----------------------------------------------------------------------
    # STEP 4: Fresh SSH keypair for THIS install specifically -- not a
    # shared master key reused across every VM this installer ever
    # creates. Marginally more work per install, but means a single
    # compromised key never grants access to more than the one VM it
    # was actually generated for.
    # -----------------------------------------------------------------------
    Write-Log "Step 4: Generating a fresh SSH keypair for this VM..."
    $SshDir = Join-Path $InstallDir "ssh"
    New-Item -ItemType Directory -Path $SshDir -Force | Out-Null
    $SshKeyPath = Join-Path $SshDir "id_ed25519"
    if (Test-Path $SshKeyPath) { Remove-Item $SshKeyPath -Force }
    if (Test-Path "$SshKeyPath.pub") { Remove-Item "$SshKeyPath.pub" -Force }

    & ssh-keygen.exe -t ed25519 -f $SshKeyPath -N '""' -q
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$SshKeyPath.pub")) {
        Write-Log "ssh-keygen failed to produce a keypair (exit code $LASTEXITCODE)."
        exit 1
    }
    $SshPublicKey = (Get-Content "$SshKeyPath.pub" -Raw).Trim()
    Write-Log "SSH keypair generated at $SshKeyPath"

    # -----------------------------------------------------------------------
    # STEP 5: Prepare this VM's own VHDX -- a fresh copy of the shared
    # master image (never the master itself, which every future
    # install on this machine also needs untouched), resized to this
    # VM's computed disk cap. Ubuntu's cloud image ships with
    # cloud-init's growpart/resizefs modules enabled by default, which
    # expand the actual root filesystem to fill whatever size the VHDX
    # itself is on first boot -- so resizing the VHDX here is genuinely
    # sufficient; nothing further has to happen inside the VM for the
    # filesystem to actually use the extra space.
    # -----------------------------------------------------------------------
    Write-Log "Step 5: Preparing this VM's own VHDX..."
    $VmDir = Join-Path $InstallDir $VMName
    New-Item -ItemType Directory -Path $VmDir -Force | Out-Null
    $VhdxPath = Join-Path $VmDir "$VMName.vhdx"

    Copy-Item -Path $MasterVhdxPath -Destination $VhdxPath -Force
    Resize-VHD -Path $VhdxPath -SizeBytes ([int64]$DiskCapGB * 1GB)
    Write-Log "VHDX ready at $VhdxPath, resized to ${DiskCapGB}GB"

    # -----------------------------------------------------------------------
    # STEP 6: Build the cloud-init NoCloud seed ISO -- user-data creates
    # the service account, injects the public key generated above, and
    # installs + exposes Docker exactly the way InstallDockerInWSL
    # already does for WSL2 (same systemd override technique, same
    # 0.0.0.0:2375 bind, same reasoning already proven there). No
    # docker-compose is installed inside the VM at all -- every
    # docker-compose command in this project (RunDockerSetup,
    # migration_listener.ps1) runs FROM the Windows host, pointed at
    # this VM's Docker daemon over DOCKER_HOST; only the daemon itself
    # needs to live inside the VM. network-config gives the VM its
    # static IP directly -- the internal switch has no DHCP server at
    # all, so this is the only way the VM gets a usable address.
    # -----------------------------------------------------------------------
    Write-Log "Step 6: Building cloud-init seed ISO..."
    $SeedDir = Join-Path $VmDir "seed"
    New-Item -ItemType Directory -Path $SeedDir -Force | Out-Null

    $MetaData = @"
instance-id: $VMName-$(Get-Date -Format yyyyMMddHHmmss)
local-hostname: er-servicedesk-server
"@
    Set-Content -Path (Join-Path $SeedDir "meta-data") -Value $MetaData -NoNewline

    $UserData = @"
#cloud-config
users:
  - name: svc
    groups: [sudo, docker]
    shell: /bin/bash
    sudo: ['ALL=(ALL) NOPASSWD:ALL']
    ssh_authorized_keys:
      - $SshPublicKey

package_update: true
packages:
  - curl

runcmd:
  - [ sh, -c, "curl -fsSL https://get.docker.com | sh" ]
  - [ mkdir, -p, /etc/systemd/system/docker.service.d ]
  - [ sh, -c, "printf '[Service]\nExecStart=\nExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375\n' > /etc/systemd/system/docker.service.d/override.conf" ]
  - [ systemctl, daemon-reload ]
  - [ systemctl, enable, docker ]
  - [ systemctl, restart, docker ]
"@
    Set-Content -Path (Join-Path $SeedDir "user-data") -Value $UserData -NoNewline

    $NetworkConfig = @"
version: 2
ethernets:
  eth0:
    addresses: [$StaticIP/$SubnetPrefixLength]
    gateway4: $HostIP
    nameservers:
      addresses: [$HostIP, 8.8.8.8]
"@
    Set-Content -Path (Join-Path $SeedDir "network-config") -Value $NetworkConfig -NoNewline

    # oscdimg.exe (Windows ADK's Deployment Tools component) is the
    # Windows-native equivalent of genisoimage/mkisofs -- confirmed as
    # the standard way to build a "cidata"-labeled NoCloud seed ISO on
    # Windows without needing WSL or a third-party ISO tool. Always
    # installs via the direct ADK installer rather than winget, for
    # one consistent code path across this project's whole supported
    # OS matrix (Windows 10, which may not have winget's ADK support
    # at all) rather than branching on winget's availability.
    $OscdimgExe = "${env:ProgramFiles(x86)}\Windows Kits\10\Assessment and Deployment Kit\Deployment Tools\amd64\Oscdimg\oscdimg.exe"
    if (-not (Test-Path $OscdimgExe)) {
        Write-Log "oscdimg.exe not found -- installing Windows ADK Deployment Tools..."
        $AdkInstallerPath = Join-Path $InstallDir "adksetup.exe"
        Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/?linkid=2289980" -OutFile $AdkInstallerPath -UseBasicParsing
        $AdkProcess = Start-Process -FilePath $AdkInstallerPath -ArgumentList "/quiet", "/features", "OptionId.DeploymentTools", "/ceip", "off", "/norestart" -Wait -PassThru
        Write-Log "ADK installer exit code: $($AdkProcess.ExitCode)"

        if (-not (Test-Path $OscdimgExe)) {
            Write-Log "oscdimg.exe still not found after ADK install attempt (looked at $OscdimgExe). Cannot build the seed ISO."
            exit 1
        }
    }

    $SeedIsoPath = Join-Path $VmDir "seed.iso"
    & $OscdimgExe -n -m -o -lcidata "$SeedDir" "$SeedIsoPath"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $SeedIsoPath)) {
        Write-Log "oscdimg failed to build the seed ISO (exit code $LASTEXITCODE)."
        exit 1
    }
    Write-Log "Seed ISO built at $SeedIsoPath"

    # -----------------------------------------------------------------------
    # STEP 7: Create the VM itself. Generation 2, Secure Boot set to
    # the Microsoft UEFI CA template (NOT Hyper-V's default template --
    # confirmed via real research that Ubuntu's shim is signed under
    # this specific certificate authority, and Gen2 Ubuntu VMs will not
    # boot at all under the default template). AutomaticStartAction
    # Start is the one setting that actually solves the original WSL2
    # problem -- confirmed via real research (someone who deliberately
    # rebooted a Hyper-V host and never logged in) that a VM set this
    # way genuinely boots with no interactive Windows session at all,
    # unlike WSL2.
    # -----------------------------------------------------------------------
    Write-Log "Step 7: Creating VM '$VMName'..."
    New-VM -Name $VMName -Generation 2 -MemoryStartupBytes ([int64]$MemStartupGB * 1GB) `
        -VHDPath $VhdxPath -SwitchName $SwitchName | Out-Null

    Set-VMProcessor -VMName $VMName -Count $VCpuCount
    Set-VMMemory -VMName $VMName -DynamicMemoryEnabled $true `
        -StartupBytes ([int64]$MemStartupGB * 1GB) `
        -MinimumBytes ([int64]$MemMinGB * 1GB) `
        -MaximumBytes ([int64]$MemMaxGB * 1GB)

    Set-VMFirmware -VMName $VMName -EnableSecureBoot On -SecureBootTemplate "MicrosoftUEFICertificateAuthority"
    Set-VM -VMName $VMName -AutomaticStartAction Start -AutomaticStopAction ShutDown

    Add-VMDvdDrive -VMName $VMName -Path $SeedIsoPath

    # Boot order: the OS disk (VHDX) needs to come first once the
    # system is actually installed -- cloud-init runs once from the
    # attached DVD regardless of boot order, this only controls what
    # the firmware tries to boot AS an OS, which must be the VHDX, not
    # the seed ISO.
    $HardDrive = Get-VMHardDiskDrive -VMName $VMName
    Set-VMFirmware -VMName $VMName -FirstBootDevice $HardDrive

    Write-Log "VM created. Starting..."
    Start-VM -Name $VMName
}

# ---------------------------------------------------------------------------
# STEP 8: Wait for the VM to genuinely be ready -- not just "running"
# (which only means the VM process itself started), but actually
# reachable over SSH with cloud-init's provisioning (Docker install,
# daemon TCP exposure) already finished. Confirmed via a real ssh
# command succeeding, not just a raw TCP connect to port 22 -- a port
# being open doesn't mean sshd has finished starting, let alone that
# cloud-init's own runcmd steps (which run after sshd is already up)
# have completed.
# ---------------------------------------------------------------------------
Write-Log "Step 8: Waiting for VM to be reachable and provisioned..."
$SshKeyPath = Join-Path (Join-Path $InstallDir "ssh") "id_ed25519"
$Ready = $false

for ($i = 0; $i -lt 60; $i++) {
    $SshResult = & ssh.exe -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes `
        -i $SshKeyPath "svc@$StaticIP" "docker version" 2>&1
    if ($LASTEXITCODE -eq 0) {
        $Ready = $true
        Write-Log "VM is reachable and Docker responded after $($i + 1) attempt(s)."
        break
    }
    Start-Sleep -Seconds 5
}

if (-not $Ready) {
    Write-Log "VM never became reachable/ready after 60 attempts (5 minutes). Stopping here."
    exit 1
}

Write-Log "=== create_server_vm.ps1 FINISHED SUCCESSFULLY ==="
exit 0
