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

# Same reasoning as prepare_vm_image.ps1 -- this script also downloads
# the ADK installer via Invoke-WebRequest.
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$script:LastLogTime = Get-Date
$script:ScriptStartTime = $script:LastLogTime
function Write-Log {
    param([string]$Message)
    $Now = Get-Date
    $SinceLast = [math]::Round(($Now - $script:LastLogTime).TotalSeconds, 1)
    $script:LastLogTime = $Now
    "$($Now.ToString('o')) - [+${SinceLast}s] $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

# Confirmed via a real test: Get-Command itself came back completely
# empty for ssh-keygen.exe in this exact process's environment --
# meaning $env:PATH genuinely doesn't include OpenSSH's directory
# HERE, in whatever environment Setup's own process chain inherits,
# even though the tool is confirmed present and working when accessed
# through other means (a direct interactive session). Rather than
# depend on PATH at all -- which every attempt so far has, one way or
# another -- this checks the real, known candidate install locations
# directly on disk. Test-Path doesn't care about environment variables
# or process inheritance at all, only whether the file genuinely
# exists, which sidesteps whatever is actually going on with PATH here
# entirely instead of trying to work around it.

# Paired helpers for narrowly scoping the WOW64 redirection disable
# around SSH calls specifically -- see the Add-Type block above for
# why this can't just be left disabled for the whole script. Callers
# MUST use try/finally around Disable/Enter- and
# Enable-Wow64FileSystemRedirection to guarantee redirection is always
# restored, even if the wrapped call itself throws.
function Disable-Wow64FileSystemRedirection {
    $Ptr = [IntPtr]::Zero
    $Result = [ErServiceDeskWow64.NativeMethods]::Wow64DisableWow64FsRedirection([ref]$Ptr)
    Write-Log "WOW64 File System Redirection disabled: $Result"
    return $Ptr
}
function Enable-Wow64FileSystemRedirection {
    param([IntPtr]$Ptr)
    $Result = [ErServiceDeskWow64.NativeMethods]::Wow64RevertWow64FsRedirection($Ptr)
    Write-Log "WOW64 File System Redirection re-enabled: $Result"
}

function Resolve-OpenSshTool {
    param([string]$ToolName)
    # WOW64 File System Redirection is now disabled for this entire
    # script's lifetime (see Wow64DisableWow64FsRedirection above), so
    # plain System32 references resolve correctly on their own now --
    # Sysnative kept as a fallback candidate, not the primary
    # mechanism anymore, since it was confirmed unreliable as an
    # actual process-LAUNCH target even though it worked fine here for
    # simple existence checks.
    $Candidates = @(
        "$env:WINDIR\System32\OpenSSH\$ToolName",
        "$env:WINDIR\Sysnative\OpenSSH\$ToolName",
        "$env:WINDIR\SysWOW64\OpenSSH\$ToolName",
        "$env:ProgramFiles\OpenSSH\$ToolName",
        "${env:ProgramFiles(x86)}\OpenSSH\$ToolName"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            return $Candidate
        }
    }
    # Last resort, in case OpenSSH is genuinely installed somewhere
    # unusual on this particular machine -- not the primary mechanism
    # anymore, since it's the one already confirmed to fail here.
    $Cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($Cmd) {
        return $Cmd.Source
    }
    return $null
}

# Same ordering fix as prepare_vm_image.ps1 -- must exist before the
# first Write-Log call, since Out-File doesn't create missing parent
# directories on its own. In practice prepare_vm_image.ps1 already ran
# first and already created this exact folder, but this script
# shouldn't silently depend on that -- it should be correct standalone.
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

# Overwrite, not append -- each run's log should only ever contain
# THAT run, not accumulate across every run this install has ever
# had. Cheap, avoids an unbounded-growth log over months of real use.
Remove-Item -Path $LogPath -Force -ErrorAction SilentlyContinue

Write-Log "=== create_server_vm.ps1 STARTED (VMName=$VMName) ==="

# Wraps the ENTIRE rest of this script -- confirmed missing here,
# unlike prepare_vm_image.ps1 which already has this same pattern.
# With $ErrorActionPreference=Stop set above, ANY unexpected cmdlet
# error anywhere below -- not just around ssh-keygen, which real
# testing has now fully exonerated -- has been killing this script
# silently, with nothing written to the log at all. Every failure so
# far showed logging simply stopping mid-step with no error message,
# which is exactly what an uncaught terminating exception looks like.
# This wrapper won't change WHETHER something fails, only whether the
# next failure actually tells us what it was.
try {

# Explicit, early check with a clear diagnostic message -- confirmed
# via a real test failure that if Hyper-V's PowerShell module isn't
# genuinely loaded yet (most often because the feature was enabled in
# an EARLIER run but the machine was never actually rebooted
# afterward, something dism.exe's own exit code doesn't reliably
# distinguish from "already fully ready" -- see InstallHyperVFeature's
# own comment in setup.iss), this would otherwise crash opaquely deep
# inside Step 1 on whatever the first Hyper-V cmdlet happens to be,
# with no indication of what actually went wrong.
try {
    Import-Module Hyper-V -ErrorAction Stop
}
catch {
    Write-Log "Hyper-V PowerShell module could not be loaded: $_"
    Write-Log "This usually means Hyper-V was enabled in an earlier run but this machine hasn't been rebooted since. Reboot, then run Setup again."
    exit 1
}

# Direct, definitive check -- the Sysnative-first fix in
# Resolve-OpenSshTool below rests on a theory that this whole process
# chain is 32-bit (explaining why Test-Path against a CONFIRMED-to-
# exist literal System32 path came back false). But Hyper-V's own
# PowerShell module loading correctly just above is real evidence
# against that theory -- there is no 32-bit build of it at all, so a
# genuinely 32-bit process could never have gotten this far. Logging
# the real answer directly rather than leaving this as an assumption
# either way.
Write-Log "Process bitness: Is64BitProcess=$([Environment]::Is64BitProcess), Is64BitOperatingSystem=$([Environment]::Is64BitOperatingSystem)"

# Confirmed via real testing: Sysnative correctly finds files that
# exist under the real System32 (Test-Path succeeded), but is NOT
# reliable as the actual LAUNCH target for a new process -- ssh-keygen
# consistently either failed to report a real exit code or hung
# silently when invoked (via Start-Process or the bare & operator)
# using a Sysnative-prefixed path, with no exception ever thrown for
# the try/catch above to catch. That's a genuinely different problem
# from "32-bit host can't launch 64-bit exes" in general -- confirmed
# NOT true, since prepare_vm_image.ps1 already launches a genuine
# 64-bit qemu-img.exe successfully from this same 32-bit process,
# every single run, via a normal absolute path that was never under
# System32 in the first place and so was never subject to redirection
# at all.
#
# Disabling WOW64 File System Redirection is the standard, more
# robust fix for the ssh-keygen/ssh problem specifically -- but
# confirmed via a real, separate failure that leaving it disabled for
# the WHOLE script breaks something else entirely: Get-WindowsCapability
# (used just below, and elsewhere) depends on its own DISM PowerShell
# module loading a NATIVE support DLL that must match this process's
# own bitness -- with redirection disabled, that module tried to load
# the genuine 64-bit DismApi.dll into this 32-bit process, which is a
# hard CPU-architecture impossibility, not a file-path issue at all.
# ssh-keygen/ssh need redirection OFF; Get-WindowsCapability needs it
# ON -- contradictory requirements in the same process. Only the
# P/Invoke TYPE DEFINITIONS live here; the actual disable/re-enable
# happens narrowly scoped around the SSH calls specifically (Steps 4
# and 8), each wrapped in try/finally so redirection is always
# restored to its normal state before anything else in this script
# (including further Dism-dependent code) runs.
Add-Type -Namespace ErServiceDeskWow64 -Name NativeMethods -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern bool Wow64DisableWow64FsRedirection(ref System.IntPtr ptr);
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern bool Wow64RevertWow64FsRedirection(System.IntPtr ptr);
"@

# Same reasoning as the Hyper-V check above -- explicit, early, with a
# clear message, rather than crashing opaquely later (confirmed via a
# real test failure that this exact thing happens: ssh-keygen.exe
# below, in Step 4, simply isn't present on a fresh Windows Server
# machine the way it commonly already is on Windows 10/11 client
# editions). OpenSSH Client is delivered as a Windows CAPABILITY, a
# different mechanism from Hyper-V's Feature/Role -- and confirmed to
# not require a restart to install, unlike Hyper-V.
$OpenSshCapabilityName = "OpenSSH.Client~~~~0.0.1.0"
$OpenSshCapability = Get-WindowsCapability -Online -Name $OpenSshCapabilityName
if ($OpenSshCapability.State -ne "Installed") {
    Write-Log "OpenSSH Client not installed -- installing now..."
    try {
        Add-WindowsCapability -Online -Name $OpenSshCapabilityName | Out-Null
        Write-Log "OpenSSH Client installed successfully."
    }
    catch {
        Write-Log "Failed to install OpenSSH Client: $_"
        exit 1
    }
}
else {
    Write-Log "OpenSSH Client already installed."
}

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

    # vCPU: a quarter of the host's logical processors, floor 2 where
    # the host can actually support it (this stack -- Postgres, Redis,
    # FastAPI, one RQ worker -- genuinely benefits from at least that
    # much to stay responsive), ceiling 8 (a repair shop's
    # ticket/inventory load has no realistic need for more, and an
    # unbounded share would let this VM starve everything else the
    # host is doing).
    #
    # The floor is NOT allowed to exceed the host's own logical
    # processor count, though -- confirmed via a real Start-VM failure
    # ("the virtual processor...count for the virtual machine exceeds
    # the logical processor...count for the host") that Hyper-V hard-
    # rejects a VM asking for more vCPUs than the host physically has,
    # no oversubscription allowed. A floor of "2, no matter what" was
    # a real bug -- a genuinely low-spec host (a small test rig, or a
    # real repair shop running this on older/minimal hardware) needs
    # to still get a VM that can actually start, even if that means
    # just 1 vCPU, rather than fail outright asking for more than the
    # host can ever give it.
    $VCpuCount = [int](Clamp ([math]::Round($HostLogicalProcessors * 0.25)) 2 8)
    $VCpuCount = [math]::Min($VCpuCount, $HostLogicalProcessors)

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

    # Everything from resolving ssh-keygen.exe's real path through
    # actually running it happens with WOW64 redirection disabled --
    # narrowly scoped to just this block (try/finally guarantees
    # re-enabling even on failure), since the Get-WindowsCapability
    # check earlier in this script needs it in its normal, ENABLED
    # state to work at all. See the Add-Type block near the top of
    # this file for the full reasoning.
    $Wow64Ptr = Disable-Wow64FileSystemRedirection
    try {
        $SshKeyGenExe = Resolve-OpenSshTool -ToolName "ssh-keygen.exe"
        if (-not $SshKeyGenExe) {
            Write-Log "ssh-keygen.exe could not be found at any known location on this machine."
            exit 1
        }
        Write-Log "Resolved ssh-keygen.exe to: $SshKeyGenExe"
        & $SshKeyGenExe -t ed25519 -f $SshKeyPath -N '""' -q
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path "$SshKeyPath.pub")) {
            Write-Log "ssh-keygen failed (exit code $LASTEXITCODE)."
            exit 1
        }
    }
    finally {
        Enable-Wow64FileSystemRedirection -Ptr $Wow64Ptr
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
  - [ sh, -c, "curl -fsSL --connect-timeout 15 --max-time 120 https://get.docker.com | sh" ]
  - [ mkdir, -p, /etc/systemd/system/docker.service.d ]
  - [ sh, -c, "printf '[Service]\nExecStart=\nExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375\n' > /etc/systemd/system/docker.service.d/override.conf" ]
  - [ systemctl, daemon-reload ]
  - [ systemctl, enable, docker ]
  - [ systemctl, restart, docker ]
"@
    Set-Content -Path (Join-Path $SeedDir "user-data") -Value $UserData -NoNewline

    # Two earlier versions of this both made a real assumption about
    # the interface that turned out wrong in practice: first assuming
    # it was named "eth0" outright, then assuming a name-glob pattern
    # would catch whatever it actually was (a real bug -- "en*" simply
    # doesn't match "eth0"), then assuming a specific driver name.
    # None of that guessing is actually necessary. Netplan documents
    # an EMPTY match stanza as matching every adapter of that device
    # type -- no name, no driver, no assumption about the hardware at
    # all. Since this VM only ever has exactly one NIC, that's
    # sufficient and correct regardless of whatever it's actually
    # named or which driver it uses underneath.
    $NetworkConfig = @"
version: 2
ethernets:
  all-eth:
    match: {}
    set-name: eth0
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
        Invoke-WebRequest -Uri "https://go.microsoft.com/fwlink/?linkid=2289980" -OutFile $AdkInstallerPath -UseBasicParsing -TimeoutSec 300
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

# Same narrow scoping as Step 4 -- disabled only around ssh.exe's
# resolution and every call in this loop, re-enabled once the loop
# ends (success or exhausted), via try/finally.
$Wow64Ptr = Disable-Wow64FileSystemRedirection
try {
    $SshExe = Resolve-OpenSshTool -ToolName "ssh.exe"
    if (-not $SshExe) {
        Write-Log "ssh.exe could not be found at any known location on this machine."
        exit 1
    }
    Write-Log "Resolved ssh.exe to: $SshExe"

    for ($i = 0; $i -lt 60; $i++) {
        # Confirmed via a real test: 2>&1 combined with this script's
        # global $ErrorActionPreference=Stop turned ssh's routine
        # stderr output (a "connection timed out" message, completely
        # expected on early attempts before the VM has finished
        # booting -- exactly the case this retry loop exists to
        # handle) into a script-terminating exception, killing the
        # whole script on the very first attempt instead of letting it
        # retry. $SshResult's captured text was never actually used
        # anywhere -- only $LASTEXITCODE was -- so removing the
        # redirection entirely sidesteps the whole problem. The
        # try/catch below is a second layer of protection for this
        # same class of issue, in case some other native-command edge
        # case inside this loop hits the same interaction.
        # Confirmed via a real hang: this whole loop is meant to bound
        # out at 5 minutes total (60 attempts x 5 seconds), but got
        # stuck for 46+ minutes on a single attempt instead --
        # -o ConnectTimeout=5 only bounds the initial TCP handshake,
        # NOT the rest of the SSH session (authentication, or the
        # remote command itself actually running). Nothing was
        # stopping a single attempt from hanging indefinitely if
        # anything inside the VM was slow to respond past that point.
        # Start-Job/Wait-Job runs this in a genuinely separate
        # process, giving a real, enforceable per-attempt timeout --
        # if one attempt hangs, it gets abandoned and the loop moves
        # on to the next retry, rather than losing the whole budget
        # (or more) to a single stuck attempt. Targets the TCP daemon
        # endpoint specifically (-H tcp://localhost:2375), not the
        # default local Unix socket -- confirmed via an earlier real
        # failure that a plain "docker version" (hitting the local
        # socket) can succeed while dockerd's TCP listener genuinely
        # isn't up yet, which is the one thing RunDockerSetup on the
        # Windows host actually depends on.
        $SshJob = Start-Job -ScriptBlock {
            param($SshExePath, $KeyPath, $Ip)
            # Confirmed via a real failure: Start-Job runs in a
            # genuinely separate OS process, which does NOT inherit
            # the parent's WOW64-redirection-disabled state -- that's
            # per-process, not something a background job picks up
            # automatically. Even though $SshExePath was already
            # resolved to the real, correct absolute path in the
            # parent, this fresh process's own (still-enabled-by-
            # default) redirection silently sent that literal path to
            # SysWOW64 instead once it actually tried to execute it --
            # which doesn't have ssh.exe, hence "not recognized."
            # Add-Type'd types don't cross process boundaries either,
            # so this needs its own declaration, not a reference to
            # the parent's.
            Add-Type -Namespace ErServiceDeskWow64Job -Name NativeMethods -MemberDefinition @"
[System.Runtime.InteropServices.DllImport("kernel32.dll", SetLastError = true)]
public static extern bool Wow64DisableWow64FsRedirection(ref System.IntPtr ptr);
"@
            $JobWow64Ptr = [IntPtr]::Zero
            [ErServiceDeskWow64Job.NativeMethods]::Wow64DisableWow64FsRedirection([ref]$JobWow64Ptr) | Out-Null

            & $SshExePath -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes `
                -i $KeyPath "svc@$Ip" "docker -H tcp://localhost:2375 version" *> $null
            return $LASTEXITCODE
        } -ArgumentList $SshExe, $SshKeyPath, $StaticIP

        $JobCompleted = Wait-Job -Job $SshJob -Timeout 15
        if ($JobCompleted) {
            $SshExitCode = Receive-Job -Job $SshJob
            Remove-Job -Job $SshJob -Force
            if ($SshExitCode -eq 0) {
                $Ready = $true
                Write-Log "VM is reachable and Docker's TCP listener responded after $($i + 1) attempt(s)."
                break
            }
        }
        else {
            Write-Log "SSH attempt $($i + 1) did not complete within 15 seconds -- abandoning it and moving on to the next retry."
            Stop-Job -Job $SshJob
            Remove-Job -Job $SshJob -Force
        }
        Start-Sleep -Seconds 5
    }
}
finally {
    Enable-Wow64FileSystemRedirection -Ptr $Wow64Ptr
}

if (-not $Ready) {
    Write-Log "VM never became reachable/ready after 60 attempts (5 minutes). Stopping here."
    exit 1
}

Write-Log "=== create_server_vm.ps1 FINISHED SUCCESSFULLY (total runtime: $([math]::Round(((Get-Date) - $script:ScriptStartTime).TotalMinutes, 1)) minutes) ==="
exit 0

}
catch {
    Write-Log "UNCAUGHT EXCEPTION: $($_.Exception.GetType().FullName): $($_.Exception.Message)"
    Write-Log "At: $($_.InvocationInfo.PositionMessage)"
    exit 1
}
