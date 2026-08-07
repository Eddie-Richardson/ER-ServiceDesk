# ER-ServiceDesk/installer/vm_resize_listener.ps1
#
# Persistent listener letting an admin adjust the Server VM's
# RAM/CPU/disk allocation remotely from the desktop app's Settings ->
# Server Resources tab (Client mode only), the same way Migrate to
# Server sends commands to migration_listener.ps1 -- this is that same
# pattern, but for an ongoing control channel rather than a one-time
# data transfer.
#
# Genuinely different from migration_listener.ps1 in one important
# way: that listener stops itself after one successful migration,
# since its whole job is done at that point. This one has no natural
# end -- an admin might resize the VM any number of times, at any
# point after install -- so the whole accept loop is wrapped in an
# outer retry loop that reopens the listener on an unexpected failure
# instead of letting the process quietly die. Registered via a
# Scheduled Task set to run "at startup" so it also survives a reboot
# (see StartVmResizeListener in setup.iss).
#
# Authentication deliberately does NOT use a bespoke token the way
# migration does -- an admin resizing the VM later is functionally the
# same trust level as an admin RDPing into this same server directly,
# so this validates real Windows credentials (via LogonUser, the exact
# Win32 API RDP's own authentication is built on) instead of a
# separate secret to keep track of. Sent as standard HTTP Basic Auth,
# which is exactly a username/password pair -- no reason to invent a
# bespoke header scheme for something HTTP already has a standard for.
#
# Security note, worth being upfront about rather than glossing over,
# same class of tradeoff already accepted for migration_listener.ps1:
# this is plain HTTP, no TLS, so the Windows password does travel
# in cleartext on the local network during each request. Acceptable
# for a local-network admin action between machines the shop already
# controls, not something to pretend is more secure than it is.

param(
    [Parameter(Mandatory = $true)]
    [string]$InstallDir,

    [Parameter(Mandatory = $true)]
    [string]$VMName,

    [Parameter(Mandatory = $true)]
    [string]$StaticIP,

    [Parameter(Mandatory = $true)]
    [string]$SshKeyPath
)

$ErrorActionPreference = "Stop"
$LogPath = Join-Path $InstallDir "vm_resize_listener_log.txt"
$ListenPort = 8002

function Write-Log {
    param([string]$Message)
    "$(Get-Date -Format o) - $Message" | Out-File -FilePath $LogPath -Append -Encoding utf8
}

# Same helper as create_server_vm.ps1 -- confirmed via a real test on
# that script that Get-Command itself can come back completely empty
# for OpenSSH tools in this process's own environment, independent of
# PATH entirely by checking known real install locations on disk.
function Resolve-OpenSshTool {
    param([string]$ToolName)
    # Same reasoning as create_server_vm.ps1 -- Sysnative bypasses
    # WOW64 File System Redirection regardless of the calling
    # process's own bitness, so checking it first costs nothing even
    # if this particular script (a Scheduled Task, not spawned by
    # Setup.exe's own 32-bit process chain) turns out not to actually
    # need it.
    $Candidates = @(
        "$env:WINDIR\Sysnative\OpenSSH\$ToolName",
        "$env:WINDIR\System32\OpenSSH\$ToolName",
        "$env:WINDIR\SysWOW64\OpenSSH\$ToolName",
        "$env:ProgramFiles\OpenSSH\$ToolName",
        "${env:ProgramFiles(x86)}\OpenSSH\$ToolName"
    )
    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            return $Candidate
        }
    }
    $Cmd = Get-Command $ToolName -ErrorAction SilentlyContinue
    if ($Cmd) {
        return $Cmd.Source
    }
    return $null
}

# Same fix as prepare_vm_image.ps1/create_server_vm.ps1 -- must exist
# before the first Write-Log call. In practice this directory already
# exists by the time this listener ever runs (create_server_vm.ps1
# creates it first), but this shouldn't silently depend on that.
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null

Write-Log "=== vm_resize_listener.ps1 STARTED ==="

# Same defensive check as create_server_vm.ps1 -- this listener's own
# disk-resize path calls ssh.exe independently, and shouldn't silently
# assume create_server_vm.ps1 already guaranteed OpenSSH Client is
# present just because it ran first. Cheap to confirm again here.
$OpenSshCapabilityName = "OpenSSH.Client~~~~0.0.1.0"
$OpenSshCapability = Get-WindowsCapability -Online -Name $OpenSshCapabilityName
if ($OpenSshCapability.State -ne "Installed") {
    Write-Log "OpenSSH Client not installed -- installing now..."
    Add-WindowsCapability -Online -Name $OpenSshCapabilityName | Out-Null
}

# ---------------------------------------------------------------------------
# Windows credential validation via LogonUser -- the same underlying
# Win32 API RDP authentication itself is built on, confirmed as the
# standard, documented mechanism for "does this username/password
# genuinely authenticate on this machine" outside of an interactive
# logon. LOGON32_LOGON_NETWORK (not _INTERACTIVE) is deliberate here --
# this only needs to confirm the credential is valid, not create a
# full interactive desktop session for it, which would be heavier and
# unnecessary for a background service like this one.
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

function Send-JsonResponse {
    param($Response, [int]$StatusCode, $Object)
    $Response.StatusCode = $StatusCode
    $Response.ContentType = "application/json"
    $Json = $Object | ConvertTo-Json -Compress -Depth 5
    $Bytes = [System.Text.Encoding]::UTF8.GetBytes($Json)
    $Response.OutputStream.Write($Bytes, 0, $Bytes.Length)
    $Response.Close()
}

function Read-JsonBody {
    param($Request)
    $Reader = New-Object System.IO.StreamReader($Request.InputStream, $Request.ContentEncoding)
    $Text = $Reader.ReadToEnd()
    $Reader.Close()
    if ([string]::IsNullOrWhiteSpace($Text)) { return $null }
    return $Text | ConvertFrom-Json
}

# ---------------------------------------------------------------------------
# Server-side validation -- the client (desktop app) also validates
# before sending, but that's just a faster/friendlier UI check, not a
# real security boundary. This is the actual boundary: a malformed or
# malicious request (0 vCPUs, a multi-terabyte memory max, a disk cap
# bigger than the host's own disk) must be rejected here regardless of
# what the client claims, the same reasoning already applied to every
# other input this project accepts from outside itself.
# ---------------------------------------------------------------------------
function Get-HostLimits {
    $ComputerSystem = Get-CimInstance -ClassName Win32_ComputerSystem
    $HostRamGB = [math]::Round($ComputerSystem.TotalPhysicalMemory / 1GB, 1)
    $HostLogicalProcessors = $ComputerSystem.NumberOfLogicalProcessors

    $InstallDrive = (Get-Item $InstallDir).PSDrive.Name
    $Volume = Get-Volume -DriveLetter $InstallDrive -ErrorAction SilentlyContinue
    $FreeDiskGB = if ($Volume) { [math]::Round($Volume.SizeRemaining / 1GB, 1) } else { 50 }

    return @{
        HostRamGB              = $HostRamGB
        HostLogicalProcessors  = $HostLogicalProcessors
        FreeDiskGB             = $FreeDiskGB
        # Same headroom reasoning as create_server_vm.ps1's own initial
        # sizing -- the VM must never be allowed to starve the host
        # machine of memory for everything else it's doing.
        MaxMemoryGB            = [math]::Round($HostRamGB * 0.75)
    }
}

$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://+:$ListenPort/resources/")

# Outer retry loop -- unlike migration_listener.ps1 (which stops itself
# after one job), this listener has no natural end, so an unexpected
# exception should reopen it rather than let the whole process quietly
# die with nothing left running until the next reboot.
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
                    Send-JsonResponse -Response $Response -StatusCode 401 -Object @{ success = $false; message = "Invalid credentials." }
                    continue
                }

                $Path = $Request.Url.AbsolutePath
                $Limits = Get-HostLimits

                if ($Request.HttpMethod -eq "GET" -and $Path -eq "/resources/status") {
                    $VM = Get-VM -Name $VMName
                    $VhdxPath = ($VM | Get-VMHardDiskDrive).Path
                    $CurrentDiskGB = [math]::Round((Get-VHD -Path $VhdxPath).Size / 1GB, 1)

                    Send-JsonResponse -Response $Response -StatusCode 200 -Object @{
                        success              = $true
                        memory_max_gb        = [math]::Round($VM.MemoryMaximum / 1GB, 1)
                        cpu_count            = $VM.ProcessorCount
                        disk_cap_gb          = $CurrentDiskGB
                        host_ram_gb          = $Limits.HostRamGB
                        host_cpu_count       = $Limits.HostLogicalProcessors
                        host_free_disk_gb    = $Limits.FreeDiskGB
                    }
                }
                elseif ($Request.HttpMethod -eq "POST" -and $Path -eq "/resources/memory") {
                    $Body = Read-JsonBody -Request $Request
                    $NewMaxGB = [double]$Body.max_gb

                    if ($NewMaxGB -lt 1 -or $NewMaxGB -gt $Limits.MaxMemoryGB) {
                        Send-JsonResponse -Response $Response -StatusCode 400 -Object @{ success = $false; message = "Requested memory must be between 1GB and $($Limits.MaxMemoryGB)GB on this host." }
                        continue
                    }

                    # Live -- Dynamic Memory's own maximum can be
                    # changed on a running VM, no restart needed.
                    Set-VMMemory -VMName $VMName -MaximumBytes ([int64]$NewMaxGB * 1GB)
                    Write-Log "Memory max set to ${NewMaxGB}GB"
                    Send-JsonResponse -Response $Response -StatusCode 200 -Object @{ success = $true; message = "Memory maximum updated to ${NewMaxGB}GB." }
                }
                elseif ($Request.HttpMethod -eq "POST" -and $Path -eq "/resources/cpu") {
                    $Body = Read-JsonBody -Request $Request
                    $NewCount = [int]$Body.count

                    if ($NewCount -lt 1 -or $NewCount -gt $Limits.HostLogicalProcessors) {
                        Send-JsonResponse -Response $Response -StatusCode 400 -Object @{ success = $false; message = "Requested vCPU count must be between 1 and $($Limits.HostLogicalProcessors) on this host." }
                        continue
                    }

                    # NOT live -- Set-VMProcessor requires the VM to be
                    # off, a real Hyper-V limitation, not something
                    # this project can work around. The desktop app's
                    # own confirmation dialog already warns the admin
                    # about this brief restart before this request is
                    # ever sent.
                    Write-Log "Stopping VM to change vCPU count to $NewCount..."
                    Stop-VM -Name $VMName -Force
                    Set-VMProcessor -VMName $VMName -Count $NewCount
                    Start-VM -Name $VMName
                    Write-Log "vCPU count set to $NewCount, VM restarted."
                    Send-JsonResponse -Response $Response -StatusCode 200 -Object @{ success = $true; message = "vCPU count updated to $NewCount. The server has restarted." }
                }
                elseif ($Request.HttpMethod -eq "POST" -and $Path -eq "/resources/disk") {
                    $Body = Read-JsonBody -Request $Request
                    $NewCapGB = [double]$Body.cap_gb

                    $VM = Get-VM -Name $VMName
                    $VhdxPath = ($VM | Get-VMHardDiskDrive).Path
                    $CurrentDiskGB = [math]::Round((Get-VHD -Path $VhdxPath).Size / 1GB, 1)

                    # Grow-only, deliberately -- safely GROWING a live
                    # filesystem is routine; safely SHRINKING one is a
                    # much riskier operation most tools refuse to
                    # automate at all, and this project doesn't attempt
                    # it either.
                    if ($NewCapGB -le $CurrentDiskGB) {
                        Send-JsonResponse -Response $Response -StatusCode 400 -Object @{ success = $false; message = "New disk size must be larger than the current ${CurrentDiskGB}GB -- shrinking isn't supported." }
                        continue
                    }
                    if (($NewCapGB - $CurrentDiskGB) -gt $Limits.FreeDiskGB) {
                        Send-JsonResponse -Response $Response -StatusCode 400 -Object @{ success = $false; message = "Not enough free space on the host -- only $($Limits.FreeDiskGB)GB available." }
                        continue
                    }

                    # Live -- Resize-VHD works on an attached, running
                    # VM's disk. Growing the VHDX itself doesn't grow
                    # the filesystem INSIDE it automatically, though --
                    # that needs growpart + resize2fs run inside the
                    # VM afterward, over SSH, using the same per-install
                    # keypair create_server_vm.ps1 generated.
                    Resize-VHD -Path $VhdxPath -SizeBytes ([int64]$NewCapGB * 1GB)
                    Write-Log "VHDX resized to ${NewCapGB}GB, running growpart/resize2fs inside the VM..."

                    $SshExe = Resolve-OpenSshTool -ToolName "ssh.exe"
                    if (-not $SshExe) { $SshExe = "ssh.exe" }
                    & $SshExe -o StrictHostKeyChecking=no -o BatchMode=yes -i $SshKeyPath "svc@$StaticIP" `
                        "sudo growpart /dev/sda 1 && sudo resize2fs /dev/sda1"
                    if ($LASTEXITCODE -ne 0) {
                        Write-Log "growpart/resize2fs failed with exit code $LASTEXITCODE -- VHDX was resized but the filesystem inside the VM may not reflect it yet."
                        Send-JsonResponse -Response $Response -StatusCode 500 -Object @{ success = $false; message = "The disk was resized, but expanding the filesystem inside the server failed. Contact support before trying again." }
                        continue
                    }

                    Write-Log "Disk cap set to ${NewCapGB}GB"
                    Send-JsonResponse -Response $Response -StatusCode 200 -Object @{ success = $true; message = "Disk capacity updated to ${NewCapGB}GB." }
                }
                else {
                    Send-JsonResponse -Response $Response -StatusCode 404 -Object @{ success = $false; message = "Unknown endpoint." }
                }
            }
            catch {
                Write-Log "Request handling error: $_"
                try {
                    Send-JsonResponse -Response $Response -StatusCode 500 -Object @{ success = $false; message = "Internal error: $_" }
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
