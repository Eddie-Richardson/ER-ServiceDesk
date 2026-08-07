; ER-ServiceDesk-Installer/setup.iss
;
; STEP 21. Server mode moved off WSL2 entirely, onto a dedicated,
; genuine Hyper-V Linux VM -- Local mode is completely untouched by
; this, still WSL2, unchanged.
;
; Root cause this fixes: extensive real testing (many hours, several
; separate approaches, all directly tested and ruled out) confirmed
; wsl.exe fundamentally cannot run reliably with no interactive
; Windows session present at all -- a real, documented, still-open WSL
; limitation, not a bug in anything built here. Task Scheduler running
; server_startup.ps1 as SYSTEM hung wsl.exe indefinitely. An
; NSSM-wrapped genuine Windows Service (Step 20's own fix) hit a
; different symptom, "the file cannot be accessed by the system," but
; the same underlying wall. S4U logon and auto-logon-then-logout were
; both ruled out too (the former via Microsoft's own docs stating it
; runs in a non-interactive desktop; the latter via a direct test
; showing `wsl -l -v` reporting the distro Stopped the moment the
; session that started it was torn down at logout). Docker Desktop
; itself is confirmed unsupported on Windows Server entirely, for the
; same fundamental reason.
;
; A genuine Hyper-V VM sidesteps this completely -- confirmed via real
; research (someone who deliberately rebooted a Hyper-V host and never
; logged in) that a VM set to AutomaticStartAction Start genuinely
; boots at host startup with no interactive session required, unlike
; WSL2. Since the VM runs genuine Linux, the existing Docker setup --
; docker-compose.yml, the Postgres/Redis/Python images, all already
; Linux-native -- needs ZERO changes; this only relocates what HOSTS
; Docker for Server mode.
;
; Removed entirely: server_startup.ps1, wsl_port_forward.ps1, and the
; NSSM Windows Service registration (RegisterServerStartupTask) --
; every one of these existed only to fight WSL2's login-dependent
; lifecycle, which no longer applies once the VM boots on its own.
; docker-compose.yml already has restart: unless-stopped on every
; service, which is what makes containers coming back up after a VM
; reboot just work via Docker's own daemon behavior -- no Windows-side
; orchestration script needed inside the loop at all anymore.
;
; New: prepare_vm_image.ps1 (downloads Ubuntu's generic qcow2 cloud
; image, converts to a shared master VHDX via a standalone qemu-img
; build) and create_server_vm.ps1 (internal NAT switch with a static
; VM IP, dynamic per-host resource sizing, a per-install SSH keypair,
; a cloud-init NoCloud seed ISO built via oscdimg, VM creation and
; Secure Boot configuration, and a wait-until-genuinely-ready poll over
; SSH). migration_listener.ps1 needed exactly one change -- its
; DOCKER_HOST now points at the VM's static IP instead of WSL2's
; loopback address; docker cp/docker-compose exec/pg_restore all work
; identically over a remote DOCKER_HOST, so nothing else in that file
; changed. RunDockerSetup's own docker-compose calls work the same
; way -- Windows-side docker-compose reads docker-compose.yml locally
; and streams the build context to the remote daemon over the API
; connection itself, so no file-transfer step into the VM was ever
; needed for the app's own source/config, only Docker Engine itself
; needs to live inside the VM.
;
; PrepareToInstall/DetectAndInstallPrerequisites were previously ONE
; shared code path for both Local and Server -- confirmed via a real
; repo audit that there was no existing separate "Server's WSL2 path"
; to swap out cleanly. Genuine new branching (IsLocalMode/IsServerMode)
; was added rather than assuming an isolated block already existed.
;
; STEP 20. The consolidated server_startup.ps1 (Step 19 area, added
; since) still failed to reach WSL2/Docker after a real reboot, with
; wsl.exe itself hanging indefinitely -- confirmed directly, over an
; hour on a single command that returned instantly when run manually.
; Root cause confirmed as a real, documented, still-open limitation on
; Microsoft's own WSL GitHub repo: wsl.exe genuinely does not work
; correctly with no interactive user session present at all,
; regardless of which account runs it, including SYSTEM -- multiple
; separate real issues there describe this exact same symptom.
;
; Task Scheduler itself was the actual problem, not anything about
; this project's own scripts or their ordering. Fixed by replacing the
; Scheduled Task entirely with a genuine Windows Service instead (via
; NSSM, a real, widely-used, public-domain third-party tool) --
; services run in their own dedicated system session specifically
; designed for unattended background operation, never built around an
; interactive session existing at all, unlike Task Scheduler. A real,
; working precedent exists for wrapping wsl.exe this exact way. See
; RegisterServerStartupTask for the full reasoning and NSSM's own
; official documentation confirming the specific build used here.
;
; STEP 19. First real migration test surfaced two real bugs, both
; fixed:
;
; (1) The migration timed out reaching the server at all -- confirmed
; via a real test that the listener itself was genuinely running and
; correctly listening the whole time, pointing squarely at Windows
; Firewall blocking unsolicited inbound connections by default on a
; fresh Server install. Fixed by opening port 8000 (the API, needed by
; every Server install for Client connections -- untested until now,
; would very likely have hit the same wall on the next test too) and
; port 8001 (the migration listener, Migration Target only, since New
; Setup never runs it at all).
;
; (2) Once reachable, the server rejected the migration with
; "'docker' is not recognized" -- the exact same stale-environment
; problem already fixed once for RunDockerSetup's own docker-compose
; calls, just surfacing in a new place: migration_listener.ps1 and
; env_self_healing.ps1 both run as a Scheduled Task under the SYSTEM
; account, whose environment was already established before this
; installer's own setx /M PATH/DOCKER_HOST calls ran, so neither
; script reliably found docker-compose.exe or reached the daemon.
; Fixed the same way, in both files (see their own header comments):
; PATH and DOCKER_HOST set explicitly at the top of each script,
; rather than depending on inheritance.
;
; STEP 18. Step 17's nohup-based keep-alive fix was itself wrong,
; worth saying plainly. A real test showed Docker still unreachable
; well after that step reported success. Confirmed via real sources
; this is a known, documented WSL2 limitation, not a mistake in that
; command's own syntax: nohup backgrounding a process reliably keeps a
; distro alive when typed inside an already-open WSL session, but not
; when launched via the wsl command from Windows, which is what this
; installer has to do. What reliably works instead, per the same
; sources: a genuine Windows-side wsl.exe process left running,
; attached to the distro the same way a real interactive terminal
; does. Fixed both the immediate, same-session version (a direct Exec
; call with ewNoWait, since this process is designed to run forever
; and RunCommand would wait for it) and the Scheduled Task's script
; content (Start-Process, for the same detached-but-running effect).
;
; STEP 17. The full WSL2/Docker Engine chain -- WSL package, Ubuntu
; import, Docker Engine, TCP config, both CLI tools -- completed
; successfully end to end for the first time after Step 16's fix. The
; next real failure was the very last step: docker-compose unable to
; reach Docker at all, connection actively refused.
;
; Root cause, confirmed via multiple sources including a Microsoft
; engineer's own explanation on the official WSL repo: WSL2
; automatically shuts an entire distro down about 15 seconds after
; nothing is actively keeping it "in use" -- confirmed this happens
; even with an active, running systemd service inside it, via a real,
; still-open GitHub issue showing exactly that. The existing
; keep-Docker-running-after-reboot Scheduled Task started the distro,
; ran a command that exited immediately, and did nothing to prevent
; this. A real test's own timestamps confirmed this was happening
; within the same install session, not just across reboots -- over 20
; seconds elapsed between the last command touching the distro
; directly and docker-compose actually being attempted.
;
; Fixed two ways: the Scheduled Task now starts a genuine, permanent
; background process (nohup sleep infinity &, the same fix Microsoft's
; own WSL team suggests for this exact scenario) instead of a one-shot
; no-op, for future boots; and the same command now also runs
; immediately during install itself, since the Task alone only fires
; at the next boot and does nothing for the rest of this same session,
; where RunDockerSetup still needs Docker reachable moments later.
;
; STEP 16. Step 15's nested-virtualization theory was also disproven
; by a real test -- same failure, identical, even after enabling it
; and retesting clean. Worth being honest that two well-documented
; theories in a row both turned out wrong before finding the real
; cause here.
;
; The actual root cause, found via Windows' own Hyper-V compute event
; log rather than another documentation-pattern-matched guess: the
; log showed the WSL2 virtual machine itself being created
; successfully (every step logged result 0x00000000), only failing at
; the exact moment it tried to read the downloaded Ubuntu rootfs file
; -- "bsdtar: Error opening archive: Unrecognized archive format".
; That file turned out to be a 286-byte plain Apache 404 HTML page,
; not a real archive at all. Ubuntu had both renamed the file and is
; actively moving WSL image publication to a different domain
; entirely (cdimages.ubuntu.com, per their own notice) since this URL
; was first confirmed -- an external change, not anything wrong with
; this file's own logic.
;
; This also surfaced a real, general gap worth fixing everywhere, not
; just here: curl does not fail on HTTP error codes by default, so a
; 404 response gets silently saved and treated as a successful
; download. Added -f to every curl call in this file so any future
; broken URL fails immediately and clearly at the download step,
; instead of surfacing as a confusing failure much later inside WSL2
; itself, the way this one did.
;
; STEP 15. Step 14's fix was wrong -- worth saying plainly rather than
; quietly overwriting it. That step assumed the MSI wasn't correctly
; installing WSL's separate MSIX "glue package" internally, based on
; real Microsoft documentation saying the MSI is supposed to do this
; automatically. A real test disproved that directly: explicitly
; installing the same package failed with "the provided package is
; already installed" -- confirming the MSI's own internal step really
; was working correctly the whole time. That fix has been removed.
;
; The real cause turned out to be something structural to how this is
; being tested, not a bug in this file at all: WSL2 needs to create
; its own internal Hyper-V-based virtual machine, and testing is
; happening inside Hyper-V VMs themselves -- confirmed via Microsoft's
; own official WSL FAQ and their own official nested-virtualization
; documentation that this specific scenario requires nested
; virtualization to be explicitly enabled per-VM, which is not on by
; default. Critically, this has to be run on the physical Hyper-V
; host, with the target VM powered off -- something this installer,
; running inside the guest, has no visibility into or control over at
; all. If this is the real explanation, it's a real machine setting
; needed to test this in a VM, not something a real customer on a
; real physical machine would ever encounter.
;
; STEP 14. The reboot-resume mechanism worked correctly for the first
; time on real hardware after Step 13's fix -- confirmed via a real
; log showing the restart prompt, an actual reboot, and Setup
; correctly resuming on its own. That surfaced the next real bug in
; the chain: wsl --import consistently failing with a generic
; "Unspecified error", even after the WSL package MSI reported
; success.
;
; Root cause, confirmed via Microsoft's own WSL project documentation
; plus a real test ruling out the more obvious explanation: WSL ships
; as two separate pieces, an MSI and a separate MSIX "glue package"
; that Store-integration features like --import depend on. The MSI is
; supposed to install that glue package automatically as one of its
; own internal steps -- but something about running it quietly on
; this environment appears to silently skip that step, even though
; the overall MSI install reports success either way. Ruled out first:
; this is not a Windows Update / OS patch-level issue -- a fully
; updated, rebooted Server 2022 machine hit the exact same failure.
; Confirmed instead by wsl --version and wsl --update both working
; correctly (the CLI genuinely is the modern package), while --import
; specifically still failed -- consistent with the glue package being
; the one missing piece, not the CLI itself.
;
; Fixed by installing that same glue package explicitly, so it's a
; step this installer fully controls and can verify, rather than an
; invisible side effect of the MSI's own internal behavior.
;
; STEP 13. Added per-step logging throughout PrepareToInstall and
; everything it calls, writing to a persistent log file in Program
; Files -- built specifically because a real test hit a wall real
; diagnostics couldn't get past on their own. That log then revealed
; the actual bug directly: InstallWSLFeatures correctly determined a
; restart was needed, but Setup never actually paused for it --
; execution went straight into the rest of the install as if nothing
; had been requested at all.
;
; Root cause, confirmed via two independent real developer accounts
; describing this exact same scenario, not guessed: NeedsRestart is
; silently ignored by Inno's own engine unless PrepareToInstall's
; returned Result string is ALSO non-empty. The official example this
; whole mechanism was built against confirms the same pattern -- it
; always pairs NeedsRestart := True with a real, non-empty Result. An
; earlier fix (consolidating two redundant on-screen messages into
; one) emptied out Result at exactly that point, not realizing doing
; so would silently disable the whole restart mechanism -- confirmed
; as the actual cause by the real log showing this stopped happening
; at exactly that same point in the change history.
;
; Fixed by restoring real text to Result when NeedsRestart is True,
; and moving the short yes/no question into the Messages section
; instead -- keeping the one-clean-message goal from before, without
; breaking the mechanism that goal depended on.
;
; STEP 12. Real VM testing surfaced two genuine bugs in the WSL2/
; Docker Engine work (Steps 9-10), both fixed here:
;
; (1) InstallWSLFeatures only checked DISM's exit code, never Exec's
; own launch-success return value -- every other command in this file
; goes through RunCommand/RunCommandSilent, which correctly check
; both, but these two DISM calls predated that pattern. A real test
; showed exactly the symptom this would cause: no restart prompt at
; all, features silently never actually enabled. Fixed to match the
; established pattern, confirmed via a real test showing DISM actually
; ran and enabled both features correctly afterward.
;
; (2) A real test then failed at "wsl --import" with "Windows
; Subsystem for Linux must be updated to the latest version to
; proceed" -- confirmed the WSL Windows features and the WSL package
; itself are two separate things. Attempted a winget-based fix first,
; which then failed differently: winget itself isn't reliably present
; on a fresh Windows Server image, confirmed directly via a real test
; ("winget" not recognized), not assumed. Both winget-dependent steps
; (the WSL package, the Docker CLI) were replaced with pinned direct
; downloads instead -- deliberately pinned rather than tracking
; "latest" automatically, since GitHub's own "always latest" URL trick
; only works when a release's filename doesn't embed its own version
; number, and both of these do. Every pinned URL was confirmed to
; actually resolve via a real HTTP check before being hardcoded, not
; assumed from documentation or an older cached reference -- worth
; rechecking these periodically, since unlike winget none of them
; self-update.
;
; While building the Docker CLI replacement, caught a second real
; mistake before it shipped: Docker's static Windows zip does NOT
; include compose support at all (confirmed via multiple real
; sources), contradicting an earlier assumption that it did. The
; originally-planned docker-compose.bat wrapper (forwarding to "docker
; compose") would have failed too, since that plugin was never
; actually going to be there either. Fixed by downloading Docker
; Compose's own real, separate standalone Windows binary directly
; (docker/compose is a genuinely different project from docker/docker)
; and placing it as docker-compose.exe -- simpler and more correct
; than the wrapper approach it replaces.
;
; STEP 11. This step closes out the last planned feature before VM
; testing: Server's .env self-healing at boot. Confirmed a real,
; important gap while designing this -- docker-compose.yml had NO
; restart policy on any service at all, meaning even a perfectly
; healthy .env wouldn't have mattered, since containers simply
; wouldn't come back up after a reboot regardless. Fixed with
; restart: unless-stopped on all four services (in docker-compose.yml,
; not this file) -- Docker's own native mechanism for the common case.
;
; That alone isn't sufficient, though: a Docker-native restart of an
; EXISTING container does not re-read .env at all (the same lesson
; already learned the hard way earlier in this project), and a restart
; policy has nothing to restart if the containers were never created
; in the first place. env_self_healing.ps1 is what actually closes
; both gaps -- checks/restores .env exactly like desktop/env_recovery.py
; already does for Local/Client (confirmed against that file's real,
; current logic before writing this), then explicitly runs
; docker-compose up -d, registered via a Scheduled Task at every boot,
; same SYSTEM-privilege pattern already used for every other Scheduled
; Task in this installer.
;
; Both Server sub-choices, not just Migration Target -- unlike
; migration_listener.ps1, any Server install has .env and needs this
; resilience.
;
; Verified with PowerShell's own real parser (same tooling already
; used for migration_listener.ps1) -- confirmed zero syntax errors.
;
; Still unverified from this end -- Inno Setup produces a real Windows
; executable installer, and there's no way to test that outside a real
; Windows machine. The real proof is running it and reporting back
; exactly what happens.

[Setup]
AppName=ER-ServiceDesk
AppVersion=1.18.1
DefaultDirName={autopf}\ER-ServiceDesk
DisableProgramGroupPage=yes
PrivilegesRequired=admin
; Without this, Inno defaults to 32-bit install mode, and {autopf}
; resolves to "Program Files (x86)" instead of the real 64-bit
; "Program Files" -- confirmed as the actual cause of a real bug where
; the installer reported success but the desktop app (a normal 64-bit
; PyInstaller build) couldn't find anything, since the two were
; looking in genuinely different folders.
;
; x64compatible, not the older x64 -- confirmed directly against
; jrsoftware.org's own Architecture Identifiers documentation and
; their official migration guide: x64compatible matches both real x64
; Windows and Arm64 Windows 11 (via emulation), while the older x64
; (deprecated, silently substituted to x64os by the compiler) only
; matches true x64 hardware. No reason to exclude Arm64 devices for a
; normal desktop business app -- this isn't a device driver.
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=.
OutputBaseFilename=ER-ServiceDesk-Setup
; A real test proved a genuine bug: setx correctly writes DOCKER_HOST/
; PATH to the registry (confirmed directly, by reading the actual
; machine-wide environment variable back), but the actual app,
; launched later via Explorer, never picked the new values up -- since
; setx only updates the registry, not any already-running process's
; environment, and Explorer itself doesn't reload its own environment
; just because something else changed the registry. This is Inno's
; own purpose-built directive for exactly this: notifies running
; applications (notably Explorer) to reload their environment
; variables from the registry the moment install finishes, so
; anything launched afterward -- even without a reboot -- correctly
; sees the new values, confirmed directly against Inno's own official
; documentation for this directive.
ChangesEnvironment=yes

[Messages]
; Inno's own built-in text here says "run Setup again" -- wrong for
; this installer, which auto-resumes via RunOnce. The full explanation
; now lives in PrepareToInstall's own Result message instead (see
; the Code section) -- a real, confirmed Inno quirk means NeedsRestart is
; silently ignored unless Result is non-empty, so that text can't be
; empty the way an earlier attempt at avoiding duplicate messages
; assumed. Keeping this one short avoids going back to two stacked
; messages saying the same thing.
PrepareToInstallNeedsRestart=Would you like to restart now?

[Files]
; Desktop app -- Local and Client only, not Server (professional
; client-server design keeps the GUI off a headless server).
Source: "..\dist\ER-ServiceDesk\*"; DestDir: "{app}"; Flags: recursesubdirs; Check: not IsServerMode

; Backend + Docker files -- Local and Server (both sub-choices), not
; Client, which owns no database or backend at all. Everything here
; matches exactly what Dockerfile's "COPY . ." needs to find in the
; same folder as docker-compose.yml, confirmed directly against the
; real project root: requirements.txt, alembic.ini, and the alembic/
; migrations folder were all missing from an earlier draft of this
; list and would have caused a broken build/missing migrations.
Source: "..\docker-compose.yml"; DestDir: "{app}"; Check: not IsClientMode
Source: "..\Dockerfile"; DestDir: "{app}"; Check: not IsClientMode
Source: "..\requirements.txt"; DestDir: "{app}"; Check: not IsClientMode
Source: "..\alembic.ini"; DestDir: "{app}"; Check: not IsClientMode
Source: "..\alembic\*"; DestDir: "{app}\alembic"; Flags: recursesubdirs; Excludes: "__pycache__"; Check: not IsClientMode
Source: "..\app\*"; DestDir: "{app}\app"; Flags: recursesubdirs; Excludes: "__pycache__"; Check: not IsClientMode

; The migration-receiving listener -- Migration Target only, since
; that's the only path that ever needs to receive an incoming
; migration. Runs as a standalone process outside Docker entirely
; (see the file's own header comment for why) -- launched detached at
; the end of install and registered via a Scheduled Task so it
; survives a reboot before the real migration arrives, both wired in
; CurStepChanged below.
Source: "migration_listener.ps1"; DestDir: "{app}"; Check: IsMigrationTarget

; The VM resource-resize listener -- both Server sub-choices, unlike
; migration_listener.ps1 above which is Migration Target only. An
; admin might want to resize a New Setup server's resources just as
; much as a migrated one. Registered as a permanent, always-on
; Scheduled Task (not a one-time launch the way migration's listener
; is) -- see StartVmResizeListener below; this one has no natural end,
; since resizing could happen any number of times after install.
Source: "vm_resize_listener.ps1"; DestDir: "{app}"; Check: IsServerMode

; .env self-healing + container startup at boot -- both Server
; sub-choices, unlike migration_listener.ps1 above which is Migration
; Target only. Any Server install has .env and needs this resilience,
; not just one that's specifically waiting to receive a migration.
; env_self_healing.ps1 has been removed -- its logic is now fully
; replicated by server_startup.ps1's own Step 4, run in guaranteed
; order as part of one consolidated boot sequence instead of as a
; separate, unordered Scheduled Task.

; VM creation scripts -- Server mode's Hyper-V VM replaces WSL2 for
; Server entirely (see the header comment at the top of this file for
; the full reasoning). Flags: dontcopy, NOT a normal install -- these
; need to run during PrepareToInstall, which happens BEFORE Inno's
; normal file-copy step, so {app} doesn't exist yet at the point
; they're needed. ExtractTemporaryFile (see CreateServerVM below) is
; the confirmed, standard Inno mechanism for exactly this: pulling a
; bundled file out to {tmp} on demand from within Pascal code, rather
; than waiting for the normal install-time copy. Both Server
; sub-choices -- New Setup and Migration Target both need a real VM to
; put Docker in.
Source: "prepare_vm_image.ps1"; Flags: dontcopy; Check: IsServerMode
Source: "create_server_vm.ps1"; Flags: dontcopy; Check: IsServerMode

[Tasks]
; Optional desktop icon, unchecked by default (opt-in, not opt-out) --
; standard Inno convention. Not offered for Server, which has no exe
; installed at all -- same condition already used for the exe itself
; in the Files section above.
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Check: not IsServerMode

[Icons]
; {autoprograms}/{autodesktop} automatically resolve to the all-users
; form now that PrivilegesRequired=admin (rather than the per-user form
; they'd resolve to under a lowest-privilege install) -- confirmed
; against a real official Inno example script. This is the actual
; desired behavior here: every employee logging into a shared PC sees
; the shortcut, not just whoever happened to run the installer.
Name: "{autoprograms}\ER-ServiceDesk"; Filename: "{app}\ER-ServiceDesk.exe"; Check: not IsServerMode
Name: "{autodesktop}\ER-ServiceDesk"; Filename: "{app}\ER-ServiceDesk.exe"; Tasks: desktopicon; Check: not IsServerMode

[Code]
const
  { Registry values settings_manager.py reads on every launch. A local
    const inside WriteRegistryValues (declared right after the
    procedure header, before begin) is not supported by this Pascal
    Script dialect -- confirmed by a real compile failure -- so this
    lives here as a global constant instead. }
  RegPath = 'Software\ERServiceRepairNC\ER-ServiceDesk\deployment';

  { Used by InstallDockerInWSL below. Local const blocks (declared
    right after a function header, before begin) aren't supported by
    this Pascal Script dialect -- confirmed by two separate real
    compile failures tonight, this being the second -- so these live
    here as global constants instead, same fix as RegPath above.

    WSLRootfsUrl's filename changed since this was first confirmed --
    a real test showed a 286-byte plain 404 HTML page being silently
    downloaded and treated as success (curl doesn't fail on HTTP error
    codes by default, now fixed -- see RunCommand's own -f flag added
    to every curl call in this file), which only surfaced much later
    as a confusing "Unrecognized archive format" failure inside WSL2
    itself, well after the real cause. Confirmed directly against
    Ubuntu's own live server as of 2026-07-29: the file itself is
    genuinely still there, just renamed
    (ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz, not
    ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz). Worth knowing this
    domain is also actively being deprecated in favor of
    cdimages.ubuntu.com per Ubuntu's own notice on this same page --
    this fix keeps things working now, but may need to move to that
    new domain entirely at some point in the future. }
  WSLDistroName = 'ER-ServiceDesk-Docker';
  WSLRootfsUrl = 'https://cloud-images.ubuntu.com/wsl/jammy/current/ubuntu-jammy-wsl-amd64-ubuntu22.04lts.rootfs.tar.gz';

  { Server mode's Hyper-V VM -- see create_server_vm.ps1 for the full
    reasoning behind each of these. Local mode is completely untouched
    by any of this; these constants are only ever read from
    Server-mode code paths (DetectAndInstallServerPrerequisites,
    CreateServerVM, RunDockerSetup's Server branch).

    VMSubnetPrefixLength/VMNatSubnetCidr describe the same
    192.168.100.0/24 network two different ways, because
    New-NetIPAddress and New-NetNat's PowerShell cmdlets each expect
    that network expressed in a different form -- a prefix length
    integer for one, full CIDR notation for the other. }
  VMName = 'ER-ServiceDesk-Server';
  VMSwitchName = 'ER-ServiceDesk-NAT';
  VMHostIP = '192.168.100.1';
  VMStaticIP = '192.168.100.10';
  VMSubnetPrefixLength = '24';
  VMNatSubnetCidr = '192.168.100.0/24';

var
  ModePage: TInputOptionWizardPage;
  ServerSubChoicePage: TInputOptionWizardPage;
  CredentialsPage: TInputQueryWizardPage;
  ClientAddressPage: TInputQueryWizardPage;
  MigrationTargetToken: String;
  MigrationTokenMemo: TNewMemo;
  { Reboot-resume state -- see PrepareToInstall/CreateRunOnceEntry/
    InitializeSetup below. RestartedFromReboot is True only when this
    exact Setup.exe was automatically re-launched by Windows (via a
    RunOnce registry entry) after a reboot that WE triggered partway
    through a previous run, to finish enabling WSL2. The five Resumed*
    values are read back from that RunOnce entry's command line and
    used to silently re-populate the wizard pages above, so the person
    never has to re-enter anything they already answered before the
    reboot happened. }
  RestartedFromReboot: Boolean;
  ResumedModeIndex: Integer;
  ResumedSubChoiceIndex: Integer;
  ResumedGmailAddress: String;
  ResumedGmailPassword: String;
  ResumedBusinessName: String;
  { Set True inside InstallDockerInWSL once it genuinely runs --
    RunDockerSetup checks this to decide whether to explicitly force
    PATH/DOCKER_HOST for its own docker-compose calls. Needed
    conditionally, not always: a real test proved Setup.exe's own
    process never picks up setx's PATH/DOCKER_HOST changes made
    earlier in the same run (setx only affects future processes), so
    docker-compose calls from Setup.exe itself need those values
    forced explicitly. But forcing them unconditionally would be wrong
    on a machine that already has Docker Desktop (skipping this whole
    WSL2 path entirely) -- Docker Desktop typically connects via a
    named pipe, not TCP, so forcing DOCKER_HOST to a TCP address there
    would break a connection that was already working correctly. }
  UsedWSL2DockerEngine: Boolean;
  { Same idea as UsedWSL2DockerEngine above, for Server mode's Hyper-V
    VM instead -- RunDockerSetup checks this to decide whether its own
    docker-compose calls need DOCKER_HOST forced explicitly at the VM's
    static IP. Set True inside CreateServerVM once it genuinely runs. }
  UsedServerVM: Boolean;

{ Runs once, before anything else -- including before InitializeWizard
  creates any page. Reads the /restart=1 command-line parameter that
  CreateRunOnceEntry below writes into the RunOnce registry entry it
  creates, confirmed as the correct, standard mechanism for this via a
  real official Inno Setup example script (CodePrepareToInstall.iss)
  demonstrating this exact reboot-mid-install-and-resume scenario. }
function InitializeSetup(): Boolean;
begin
  RestartedFromReboot := ExpandConstant('{param:restart|0}') = '1';

  if RestartedFromReboot then
  begin
    ResumedModeIndex := StrToIntDef(ExpandConstant('{param:modeidx|0}'), 0);
    ResumedSubChoiceIndex := StrToIntDef(ExpandConstant('{param:subidx|0}'), 0);
    ResumedGmailAddress := ExpandConstant('{param:gmailaddr|}');
    ResumedGmailPassword := ExpandConstant('{param:gmailpass|}');
    ResumedBusinessName := ExpandConstant('{param:bizname|}');
  end;

  Result := True;
end;

procedure InitializeWizard;
begin
  ModePage := CreateInputOptionPage(wpWelcome,
    'Choose Install Mode',
    'How will this installation be used?',
    'Select one of the following options, then click Next to continue.',
    True, False);
  ModePage.Add('Local -- everything runs on this PC (the right choice if you''re the only one using it)');
  ModePage.Add('Server -- this PC hosts the shared backend for other PCs to connect to');
  ModePage.Add('Client -- connect to a server already set up on another PC');
  ModePage.SelectedValueIndex := 0;
  if RestartedFromReboot then
    ModePage.SelectedValueIndex := ResumedModeIndex;

  ServerSubChoicePage := CreateInputOptionPage(ModePage.ID,
    'Server Setup Type',
    'Is this a brand new server, or the target of a migration from an existing Local install?',
    'This page only appears because Server was selected. Select one of the following options, then click Next to continue.',
    True, False);
  ServerSubChoicePage.Add('New Setup -- set up a brand new server from scratch');
  ServerSubChoicePage.Add('Migration Target -- this server will receive data migrated from an existing Local install');
  ServerSubChoicePage.SelectedValueIndex := 0;
  if RestartedFromReboot then
    ServerSubChoicePage.SelectedValueIndex := ResumedSubChoiceIndex;

  { Gmail credentials + business name. Only shown for Local and
    Server -> New Setup, via ShouldSkipPage below. }
  CredentialsPage := CreateInputQueryPage(ServerSubChoicePage.ID,
    'Email & Business Details',
    'This information is used to send email notifications to customers.',
    'Enter your Gmail address, its App Password (not your regular Gmail password), and your business name.');
  CredentialsPage.Add('Gmail Address:', False);
  CredentialsPage.Add('Gmail App Password:', True);
  CredentialsPage.Add('Business Name:', False);
  if RestartedFromReboot then
  begin
    CredentialsPage.Values[0] := ResumedGmailAddress;
    CredentialsPage.Values[1] := ResumedGmailPassword;
    CredentialsPage.Values[2] := ResumedBusinessName;
  end;

  { Server address. Only shown for Client, via ShouldSkipPage below. }
  ClientAddressPage := CreateInputQueryPage(CredentialsPage.ID,
    'Server Address',
    'Where is the ER-ServiceDesk server located?',
    'Enter the address of the PC running Server mode, e.g. 192.168.1.50');
  ClientAddressPage.Add('Server Address:', False);
end;

function IsLocalMode(): Boolean;
begin
  Result := ModePage.SelectedValueIndex = 0;
end;

function IsServerMode(): Boolean;
begin
  Result := ModePage.SelectedValueIndex = 1;
end;

function IsClientMode(): Boolean;
begin
  Result := ModePage.SelectedValueIndex = 2;
end;

function IsNewServerSetup(): Boolean;
begin
  Result := IsServerMode() and (ServerSubChoicePage.SelectedValueIndex = 0);
end;

function IsMigrationTarget(): Boolean;
begin
  Result := IsServerMode() and (ServerSubChoicePage.SelectedValueIndex = 1);
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  { On a resumed run, every one of our OWN custom pages gets skipped
    unconditionally -- the person already answered these before the
    reboot, and InitializeWizard above already silently restored those
    answers into the same page objects. They should never see the
    wizard a second time.

    A real, reproducible bug: this used to return True for EVERY
    PageID whenever RestartedFromReboot was True, not just our own
    custom ones -- which meant Inno's own built-in Finished page (and
    any other built-in page) got silently skipped too, on every single
    resumed run. That's every fresh install that needed WSL2
    installed, meaning Setup just closed at the very end with no
    Finished page, no completion message, and (for Migration Target)
    no chance to ever see the migration token, even though it was
    correctly generated the whole time -- confirmed directly, not
    assumed: the token was genuinely sitting in .env, the page
    displaying it just never appeared at all. Fixed by only treating
    our own four custom pages as skippable on resume; any other
    PageID (a built-in Inno page) is never affected by resume state. }
  if RestartedFromReboot then
  begin
    Result := (PageID = ModePage.ID) or (PageID = ServerSubChoicePage.ID) or
      (PageID = CredentialsPage.ID) or (PageID = ClientAddressPage.ID);
    Exit;
  end;

  Result := False;
  if PageID = ServerSubChoicePage.ID then
    Result := ModePage.SelectedValueIndex <> 1
  else if PageID = CredentialsPage.ID then
    Result := not (IsLocalMode() or IsNewServerSetup())
  else if PageID = ClientAddressPage.ID then
    Result := not IsClientMode();
end;

{ Builds a random alphanumeric string of the given length. Letters and
  digits only -- deliberately avoids characters like @ : / that would
  need special handling if embedded inside a connection-string URL,
  the same lesson learned the hard way earlier in this project when a
  Postgres password containing an @ symbol broke DATABASE_URL parsing. }
function GenerateRandomString(const NumChars: Integer): String;
var
  Charset: String;
  I: Integer;
begin
  Charset := 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
  Result := '';
  for I := 1 to NumChars do
    Result := Result + Charset[Random(Length(Charset)) + 1];
end;

{ Writes .env to both the main install location and the separate
  backup folder -- identical content in both, so env_recovery.py can
  restore from the backup if the main copy ever goes missing. Skipped
  entirely for Client, which owns no database or backend at all. }
procedure WriteEnvFiles;
var
  EnvContent: String;
  PostgresPassword: String;
  SecretKey: String;
  BackupDir: String;
begin
  PostgresPassword := GenerateRandomString(24);
  SecretKey := GenerateRandomString(48);

  EnvContent :=
    'DATABASE_URL=postgresql+psycopg2://postgres:' + PostgresPassword + '@db:5432/erservicedesk' + #13#10 +
    'POSTGRES_USER=postgres' + #13#10 +
    'POSTGRES_PASSWORD=' + PostgresPassword + #13#10 +
    'POSTGRES_DB=erservicedesk' + #13#10 +
    'SECRET_KEY=' + SecretKey + #13#10;

  { Migration Target deliberately gets none of this -- the real Gmail
    credentials and business name arrive later via the migration
    itself, not typed in here. }
  if IsLocalMode() or IsNewServerSetup() then
  begin
    EnvContent := EnvContent +
      'GMAIL_ADDRESS=' + CredentialsPage.Values[0] + #13#10 +
      'GMAIL_APP_PASSWORD=' + CredentialsPage.Values[1] + #13#10 +
      'BUSINESS_NAME=' + CredentialsPage.Values[2] + #13#10;
  end;

  { Migration Target's one-time token, authenticating the later
    "Migrate to Server" request that actually transfers real data.
    Shown once on the Finished page (see CurPageChanged below) --
    persisted here in .env so the future migration-receiving endpoint
    can read and verify it, since Server has no other way to hold
    state (no exe, no registry writes). Building that endpoint itself
    is separate, later work -- this just generates and stores the
    token, and shows it to the admin. }
  if IsMigrationTarget() then
  begin
    MigrationTargetToken := GenerateRandomString(32);
    EnvContent := EnvContent + 'MIGRATION_TOKEN=' + MigrationTargetToken + #13#10;
  end;

  SaveStringToFile(ExpandConstant('{app}\.env'), EnvContent, False);

  BackupDir := ExpandConstant('{autopf}\ER-ServiceDesk-Backup');
  ForceDirectories(BackupDir);
  SaveStringToFile(BackupDir + '\.env', EnvContent, False);
end;

{ Writes the Windows Registry values the desktop app's
  settings_manager.py reads on every launch (install_mode,
  backend_url, business_name). Server mode gets none of this -- it has
  no exe installed at all, so nothing there would ever read them. }
procedure WriteRegistryValues;
begin
  if IsLocalMode() then
  begin
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'install_mode', 'local');
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'backend_url', 'http://localhost:8000');
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'business_name', CredentialsPage.Values[2]);
  end
  else if IsClientMode() then
  begin
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'install_mode', 'client');
    { A real test found a genuine bug: the field only ever asks for a
      bare IP address, but the raw text was being saved exactly as
      typed, with nothing added -- producing an invalid URL missing
      both the scheme and port entirely, which every part of the app
      that uses this value would silently fail against. http:// and
      :8000 are fixed defaults that never change here, so they're
      added automatically now rather than depending on someone typing
      a complete URL into a field that only ever asked for an IP. }
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'backend_url', 'http://' + ClientAddressPage.Values[0] + ':8000');
  end;
end;

{ Writes a timestamped line to a persistent log file directly in
  Program Files -- deliberately not inside the app install folder or
  the WSL install folder, since neither exists yet when this is first
  called from PrepareToInstall, and deliberately not the temp folder
  either, since that may not even be the same folder after the
  reboot-resume relaunch. Program Files itself always exists and this
  installer already runs as admin, so writing directly into it works
  reliably from the very first line of PrepareToInstall onward.

  Built specifically because real testing hit a wall real diagnostics
  couldn't get past: a step failed with no earlier error shown, and no
  way to tell how far the install actually got before that happened.
  Every command this installer runs now gets recorded here -- attempt
  and result -- so the next failure shows exactly where it stopped,
  without needing another round of guessing. }
procedure LogStep(const Message: String);
var
  LogPath: String;
  Timestamp: String;
begin
  LogPath := ExpandConstant('{autopf}\ER-ServiceDesk-Install-Log.txt');
  Timestamp := GetDateTimeString('yyyy-mm-dd hh:nn:ss', '-', ':');
  SaveStringToFile(LogPath, Timestamp + ' - ' + Message + #13#10, True);
end;

{ Same as RunCommand, but never shows an error dialog -- for the rare
  step that's genuinely fine to fail silently (e.g. a folder that
  might already exist from a prior attempt, or a best-effort
  convenience wrapper that isn't load-bearing). Using RunCommand
  itself for these would be wrong -- it always shows a "Setup step
  failed" dialog on failure, which would be a confusing, scary message
  for something that's actually an expected, harmless outcome.

  WorkingDir is a real parameter now, not hardcoded to the app install
  folder -- a real bug caught this: that folder (Program Files\
  ER-ServiceDesk) doesn't exist yet when this is called from
  PrepareToInstall, which runs before Inno copies any files at all.
  Passing that nonexistent folder as the working directory made
  Exec() itself fail outright, unrelated to whether the actual command
  would have succeeded. Callers during PrepareToInstall should pass
  the temp folder instead (always exists); RunDockerSetup's own calls,
  which run later during ssPostInstall once the real app folder
  genuinely exists and needs to be the working directory for
  docker-compose to find docker-compose.yml, correctly still pass
  that. }
procedure RunCommandQuiet(const Params, WorkingDir: String);
var
  ResultCode: Integer;
  Launched: Boolean;
begin
  LogStep('RunCommandQuiet attempting: ' + Params);
  Launched := Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Launched then
    LogStep('RunCommandQuiet finished, exit code ' + IntToStr(ResultCode) + ': ' + Params)
  else
    LogStep('RunCommandQuiet FAILED TO LAUNCH: ' + Params);
end;

{ Same as RunCommand, but never shows an error dialog AND returns the
  actual success/failure result -- for detection/probe steps where
  failure is a normal, expected outcome, not an error. Checking
  whether Docker already exists is exactly this: failing is the
  entire scenario this feature exists to handle, not something that
  should ever pop up a "Setup step failed" dialog. Using RunCommand
  for that specific check was a real bug, caught by a real test. }
function RunCommandSilent(const Params, WorkingDir: String): Boolean;
var
  ResultCode: Integer;
  ResultText: String;
begin
  LogStep('RunCommandSilent attempting: ' + Params);
  Result := Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := ResultCode = 0;
  if Result then
    ResultText := 'True'
  else
    ResultText := 'False';
  LogStep('RunCommandSilent result: ' + ResultText + ' (exit code ' + IntToStr(ResultCode) + '): ' + Params);
end;

{ Runs a command via cmd.exe (so PATH-based tool resolution works the
  same as typing it in a real command prompt), waits for it to finish,
  and shows a clear error naming exactly what failed and what command
  to try manually if it did -- rather than leaving someone with a
  silently half-configured install and no idea why. }
function RunCommand(const Description, Params, WorkingDir: String): Boolean;
var
  ResultCode: Integer;
  ResultText: String;
begin
  LogStep('RunCommand attempting [' + Description + ']: ' + Params);
  Result := Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := ResultCode = 0;
  if Result then
    ResultText := 'True'
  else
    ResultText := 'False';
  LogStep('RunCommand result for [' + Description + ']: ' + ResultText + ' (exit code ' + IntToStr(ResultCode) + ')');
  if not Result then
    MsgBox('Setup step failed: ' + Description + #13#13 +
      'ER-ServiceDesk is installed at ' + ExpandConstant('{app}') + '. ' +
      'You may be able to fix this by running the following manually ' +
      'from that folder:' + #13#13 + Params, mbError, MB_OK);
end;

{ Wraps a string in double quotes -- needed for command-line/registry
  values that might contain spaces (a business name almost certainly
  will). Matches the same small helper function the confirmed official
  Inno example for this exact scenario (CodePrepareToInstall.iss)
  defines itself, rather than assuming a built-in exists. }
function Quote(const S: String): String;
begin
  Result := '"' + S + '"';
end;

{ Writes a RunOnce registry entry pointing back at this same Setup.exe
  with a /restart=1 flag, plus everything needed to silently restore
  the wizard's answers on the resumed run (see InitializeSetup and
  InitializeWizard above) -- confirmed as the correct, standard
  mechanism via a real official Inno example script demonstrating this
  exact scenario (CodePrepareToInstall.iss).

  Worth being explicit about a real, narrow tradeoff here: the Gmail
  app password sits in this RunOnce entry (HKEY_LOCAL_MACHINE,
  readable by any local account) in plain text for the brief window
  between now and the next reboot. This mirrors the official example's
  own pattern (which also passes plain command-line params for its
  own custom data), and the exposure window is short and requires
  local machine access -- but it's a real, deliberate tradeoff, not an
  oversight, worth knowing about rather than glossing over. }
procedure CreateRunOnceEntry;
var
  RunOnceData: String;
begin
  RunOnceData := Quote(ExpandConstant('{srcexe}')) + ' /restart=1';
  RunOnceData := RunOnceData + ' /modeidx=' + IntToStr(ModePage.SelectedValueIndex);
  RunOnceData := RunOnceData + ' /subidx=' + IntToStr(ServerSubChoicePage.SelectedValueIndex);
  RunOnceData := RunOnceData + ' /gmailaddr=' + Quote(CredentialsPage.Values[0]);
  RunOnceData := RunOnceData + ' /gmailpass=' + Quote(CredentialsPage.Values[1]);
  RunOnceData := RunOnceData + ' /bizname=' + Quote(CredentialsPage.Values[2]);
  RegWriteStringValue(HKEY_LOCAL_MACHINE, 'Software\Microsoft\Windows\CurrentVersion\RunOnce', 'ER-ServiceDeskResume', RunOnceData);
end;

{ Enables the two Windows features WSL2 (and therefore Docker Engine)
  needs. Exit code 3010 is a well-established, standard Windows
  convention meaning "succeeded, but a restart is required before this
  takes effect" -- as opposed to 0, meaning success with nothing
  further needed (e.g. the feature was already enabled).

  A real test caught a genuine bug here: this used to check only
  ResultCode, never Exec's own launch-success return value -- every
  other command in this whole file goes through RunCommand or
  RunCommandSilent, which both correctly check both things, but these
  two calls predated that pattern and were never brought in line with
  it. If dism.exe ever failed to actually launch at all, ResultCode
  would be left holding whatever leftover, meaningless value happened
  to already be in that variable -- not a real result -- and this
  function would silently continue as if DISM had succeeded, never
  setting NeedsRestart, never reporting failure. That's consistent
  with exactly what a real test showed: no restart prompt at all, and
  the rest of the install proceeding as if WSL2 were already active
  when it genuinely wasn't. Also now passing the temp folder as the
  working directory instead of an empty string, matching every other Exec()
  call in this file -- an invalid working directory is a separate,
  already-confirmed way for Exec() to fail to launch at all. }
function InstallWSLFeatures(var NeedsRestart: Boolean): Boolean;
var
  ResultCode: Integer;
  Launched: Boolean;
begin
  NeedsRestart := False;
  Result := True;

  Launched := Exec('dism.exe', '/online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart', ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not Launched then
  begin
    Result := False;
    Exit;
  end;
  if ResultCode = 3010 then
    NeedsRestart := True
  else if ResultCode <> 0 then
  begin
    Result := False;
    Exit;
  end;

  Launched := Exec('dism.exe', '/online /enable-feature /featurename:VirtualMachinePlatform /all /norestart', ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if not Launched then
  begin
    Result := False;
    Exit;
  end;
  if ResultCode = 3010 then
    NeedsRestart := True
  else if ResultCode <> 0 then
    Result := False;
end;

{ Installs a real Linux distro inside WSL2, Docker Engine inside that
  distro, exposes it to Windows, and makes sure it's all still running
  after every reboot -- all without Docker Desktop, matching this
  project's actual target architecture.

  Uses "wsl --import" from an official Ubuntu WSL rootfs tarball,
  deliberately NOT "wsl --install -d <distro>" -- confirmed via a real,
  currently-open Microsoft WSL GitHub issue that --install (even with
  --no-launch) does not actually finish setting up a usable distro; it
  still requires an interactive "create a Unix username and password"
  prompt on first launch, which would hang this unattended install
  indefinitely waiting for input that never comes. An imported distro
  defaults to running as root automatically, sidestepping that
  interactive step entirely -- confirmed as the real technique actual
  unattended-WSL-provisioning tools use, not a workaround improvised
  here.

  This function, and the several confirmed-but-never-testable pieces
  it depends on (systemd inside WSL2, Docker's daemon.json/systemd
  override for TCP exposure, winget for the Windows-side CLI), is
  genuinely the least certain part of this whole installer -- every
  individual piece was verified as thoroughly as real research allows,
  but the full sequence has never run anywhere. This is exactly what
  the VM test exists to prove. }
{ Downloads and places the Windows-side docker.exe/docker-compose.exe
  CLI tools -- extracted out of InstallDockerInWSL so Server mode's
  Hyper-V VM path (CreateServerVM below) can call this exact same
  function instead of duplicating it. Both paths need these tools for
  the same reason: whatever's actually running Docker (WSL2 for Local,
  the VM for Server), something on the WINDOWS side still needs
  docker.exe/docker-compose.exe on PATH to talk to it -- this function
  doesn't care which.

  Same reasoning as the WSL rootfs download elsewhere in this file --
  winget isn't reliably present on a fresh Windows Server image,
  confirmed by a real test, so this is a pinned direct download
  instead. Docker's static CLI ships as a plain zip (not an
  installer), extracting to a "docker" subfolder containing docker.exe
  -- confirmed directly by fetching Docker's own real directory
  listing as of 2026-07-28, not assumed from an older or cached
  reference. Worth rechecking periodically, since this won't
  self-update the way winget would have. }
function InstallDockerCLIOnWindows(const InstallDir: String): Boolean;
begin
  Result := False;

  { --connect-timeout/--max-time added after a real, confirmed hang:
    Setup sat at "Preparing to Install" for over 4 hours with no
    indication anything was wrong, because this curl call (and every
    other download in this installer) had no timeout at all -- a
    stalled connection just waited forever, and so did Exec()
    waiting on it. Every download below gets the same fix. }
  if not RunCommand('Downloading Windows Docker CLI tools',
    'curl -f -L --connect-timeout 15 --max-time 300 -o "' + InstallDir + '\docker-cli.zip" https://download.docker.com/win/static/stable/x86_64/docker-29.5.3.zip', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Extracting Windows Docker CLI tools',
    'powershell -Command "Expand-Archive -Path ''' + InstallDir + '\docker-cli.zip'' -DestinationPath ''' + InstallDir + ''' -Force"', ExpandConstant('{tmp}')) then Exit;

  { A real, caught-before-shipping mistake: Docker's static Windows
    zip does NOT include compose support at all -- confirmed via
    multiple real sources after first wrongly assuming the "docker
    compose" plugin was bundled in. Compose is a genuinely separate
    project (docker/compose, not docker/docker) with its own releases
    and its own standalone Windows binary. Downloading that directly
    and placing it as docker-compose.exe -- the exact name this
    installer's already-tested code already expects -- is simpler and
    more correct than the wrapper-batch-file approach this replaces:
    no uncertainty about percent-sign doubling, no dependency on a
    plugin that was never actually going to be there. Filename
    confirmed lowercase via a real HTTP check, not assumed from an
    older, differently-cased reference some guides still show. }
  if not RunCommand('Downloading Docker Compose',
    'curl -f -L --connect-timeout 15 --max-time 300 -o "' + InstallDir + '\docker-compose.exe" https://github.com/docker/compose/releases/download/v5.3.1/docker-compose-windows-x86_64.exe', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Making Docker commands available',
    'setx /M PATH "%PATH%;' + InstallDir + ';' + InstallDir + '\docker"', ExpandConstant('{tmp}')) then Exit;

  Result := True;
end;

function InstallDockerInWSL: Boolean;
var
  InstallDir, TarballPath: String;
  KeepAliveResultCode: Integer;
  KeepAliveLaunched: Boolean;
begin
  Result := False;
  InstallDir := ExpandConstant('{autopf}\ER-ServiceDesk-WSL');
  TarballPath := InstallDir + '\ubuntu-rootfs.tar.gz';
  LogStep('=== InstallDockerInWSL STARTED, InstallDir=' + InstallDir + ' ===');
  UsedWSL2DockerEngine := True;

  RunCommandQuiet('mkdir "' + InstallDir + '"', ExpandConstant('{tmp}'));
  { Failing here because the folder already exists from a prior
    attempt isn't a real problem -- keep going rather than treat it as
    fatal. }

  if not RunCommand('Downloading Ubuntu for WSL (this can take a few minutes)',
    'curl -f -L --connect-timeout 15 --max-time 900 -o "' + TarballPath + '" ' + WSLRootfsUrl, ExpandConstant('{tmp}')) then Exit;

  { The WSL2 Windows features (DISM, above) and the WSL2 package
    itself are two separate things -- confirmed by a real test that
    failed here specifically with "Windows Subsystem for Linux must
    be updated to the latest version to proceed." Originally used
    winget for this, but a real test showed winget itself isn't
    reliably present on a fresh Windows Server image -- confirmed
    directly, not assumed. Pinned to a specific version instead of
    tracking "latest" automatically, since GitHub's own "always
    latest" URL trick only works when a release's filename doesn't
    change between versions, and this one does (each release embeds
    its own version number in the filename). This URL was confirmed
    to actually resolve (a real HTTP 200, correct filename in the
    response) as of 2026-07-28 -- worth rechecking periodically, since
    unlike winget this won't self-update. }
  if not RunCommand('Downloading Windows Subsystem for Linux',
    'curl -f -L --connect-timeout 15 --max-time 300 -o "' + InstallDir + '\wsl-package.msi" https://github.com/microsoft/WSL/releases/download/2.7.8/wsl.2.7.8.0.x64.msi', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Installing Windows Subsystem for Linux',
    'msiexec /i "' + InstallDir + '\wsl-package.msi" /quiet /norestart', ExpandConstant('{tmp}')) then Exit;

  { A real test showed the MSI above completing successfully
    (exit code 0) while wsl --import still failed every time with a
    generic "Unspecified error". Explicitly installing the MSIX glue
    package here was tried as a fix, based on real documentation that
    the MSI is supposed to install it automatically -- but a real
    test proved that theory wrong: it failed with "the provided
    package is already installed", confirming the MSI's own internal
    step genuinely was working correctly all along. That fix has been
    removed. The real cause turned out to be something else entirely
    -- see the header comment at the top of this file for what
    actually explained it. }
  if not RunCommand('Importing Ubuntu into WSL2',
    'wsl --import ' + WSLDistroName + ' "' + InstallDir + '" "' + TarballPath + '"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Enabling systemd inside WSL',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "printf ''[boot]\nsystemd=true\n'' > /etc/wsl.conf"', ExpandConstant('{tmp}')) then Exit;

  { Restarts the whole WSL subsystem so the systemd config just
    written actually takes effect -- the distro's next launch (the
    very next command below) will have systemd as PID 1. }
  if not RunCommand('Restarting WSL to apply systemd', 'wsl --shutdown', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Installing Docker Engine inside WSL (this can take a few minutes)',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "curl -fsSL --connect-timeout 15 --max-time 120 https://get.docker.com | sh"', ExpandConstant('{tmp}')) then Exit;

  { Confirmed via real sources this is the correct way to expose
    Docker's daemon over TCP -- a systemd override clearing the
    distro's default ExecStart (which already specifies its own -H
    flag) and replacing it with one that includes both the Unix socket
    and a TCP listener. Editing daemon.json's "hosts" key instead, on
    its own, conflicts with the unit file's own -H flag and prevents
    Docker from starting at all -- confirmed as a real, known issue,
    not a guess.

    Binds to 0.0.0.0, not 127.0.0.1 -- a real test proved 127.0.0.1
    wrong here, and it cost real time chasing the wrong theory (WSL2
    auto-shutdown) before this was found. Confirmed via multiple real
    sources: a service bound to loopback inside WSL2 is not reliably
    reachable from Windows even with WSL2's own localhost forwarding
    active -- one source put it as "forwarding into a brick wall."
    Windows' own DOCKER_HOST below correctly stays 127.0.0.1, since
    that's Windows' own localhost, which WSL2 forwards into the distro
    specifically when the service inside is listening on all
    interfaces, not the other way around. }
  if not RunCommand('Configuring Docker to be reachable from Windows',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "mkdir -p /etc/systemd/system/docker.service.d && printf ''[Service]\nExecStart=\nExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://0.0.0.0:2375\n'' > /etc/systemd/system/docker.service.d/override.conf"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Starting Docker',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "systemctl daemon-reload && systemctl enable docker && systemctl restart docker"', ExpandConstant('{tmp}')) then Exit;

  { Keeps this same distro alive for the REST of this install run --
    the Scheduled Task below only fires at the NEXT boot, which does
    nothing for what happens between here and RunDockerSetup's own
    docker-compose call, still to come in this same session.

    A real test showed the nohup-based version of this step (an
    earlier attempt) did not actually work -- Docker was still
    unreachable well after it reported success. Confirmed via real
    sources this is a known, documented WSL2 limitation, not a mistake
    in that command's own syntax: nohup backgrounding a process
    reliably keeps a distro alive when typed inside an already-open
    WSL session, but does not reliably work when launched via the wsl
    command from Windows, which is what this installer has to do.
    What reliably works instead, per the same sources: keeping an
    actual Windows-side wsl.exe process running and attached to the
    distro, the same way a real interactive terminal does. This
    launches wsl.exe directly (not through RunCommand, which would
    wait for it to finish -- it's designed to run forever) and lets it
    keep running in the background for the rest of this install. }
  KeepAliveLaunched := Exec('wsl.exe', '-d ' + WSLDistroName + ' -u root -e sleep infinity', ExpandConstant('{tmp}'), SW_HIDE, ewNoWait, KeepAliveResultCode);
  if KeepAliveLaunched then
    LogStep('Launched wsl.exe -e sleep infinity to keep the distro alive for this session.')
  else
    LogStep('Failed to launch the wsl.exe keep-alive process.');

  if not InstallDockerCLIOnWindows(InstallDir) then Exit;

  { A real test proved 127.0.0.1 (IPv4) unreachable here, even though
    Docker itself was genuinely running the whole time -- confirmed
    directly: dockerd's own log showed it listening on the IPv6
    wildcard address specifically (port 2375), with no corresponding
    IPv4-specific listen line at all, and a manual connection over
    IPv6 loopback succeeded immediately where IPv4 was refused. Why
    dockerd's 0.0.0.0 flag (unambiguously an IPv4 address) resulted in an IPv6-only bind isn't fully
    understood -- worth being honest about that gap rather than
    claiming more certainty than the evidence supports -- but the fix
    itself is directly confirmed, not theoretical. }
  if not RunCommand('Configuring Docker connection',
    'setx /M DOCKER_HOST tcp://[::1]:2375', ExpandConstant('{tmp}')) then Exit;

  { Without this, the WSL distro (and Docker inside it) would not be
    running again after the next reboot -- WSL distros don't auto-start
    on their own.

    A real test showed Docker unreachable moments after a successful
    install, with the connection actively refused. Root cause,
    confirmed via multiple sources including a Microsoft engineer's
    own explanation on the official WSL repo: WSL2 automatically shuts
    an entire distro down about 15 seconds after nothing is actively
    keeping it "in use" -- and critically, this happens even with an
    active, running systemd service inside it, confirmed by a real,
    still-open GitHub issue showing exactly that. The previous
    -e /bin/true here started the distro, did nothing, and exited
    immediately -- doing nothing to prevent that shutdown. Fixed by
    starting a genuine, permanent background process instead
    (nohup sleep infinity &), the same fix Microsoft's own WSL team
    suggests for this exact scenario -- this keeps WSL2 considering
    the distro "in use" indefinitely, rather than relying on a
    one-shot command that's already finished by the time anything
    would need Docker to actually be running.

    A real test then proved the nohup-inside-Linux approach above
    itself did not work -- Docker was still unreachable well after
    that step reported success. Confirmed via real sources this is a
    known, documented WSL2 limitation: nohup backgrounding reliably
    keeps a distro alive when typed inside an already-open WSL
    session, but not when launched via the wsl command from Windows.
    What reliably works instead: a genuine Windows-side wsl.exe
    process left running, detached via Start-Process so it survives
    after this script itself exits -- the same fix as the immediate,
    same-session version of this above.

    A real test also proved embedding a command directly in schtasks'
    own /tr argument was fragile -- cmd.exe's parsing of shell
    metacharacters (&, >) nested inside escaped quotes turned out to
    be inconsistent even with a byte-verified-correct string. Fixed by
    writing a small, real script file instead and pointing schtasks at
    that simple path, with no special characters in the /tr argument
    at all -- the same pattern already proven working for
    migration_listener.ps1's own Scheduled Task.

    That separate Scheduled Task has since been replaced entirely by
    server_startup.ps1's own Step 1 -- a real test showed three
    separate, unordered "at startup" tasks (this one, port forwarding,
    and .env self-healing) could race each other, since Windows Task
    Scheduler has no real dependency mechanism between them. One
    consolidated script now handles the whole boot sequence in
    guaranteed order instead. This immediate, current-session keep-alive
    below is unrelated to that boot-time ordering problem and stays
    exactly as before. }

  Result := True;
end;

{ Orchestrates the whole prerequisite check: if Docker already works
  (Eddie's own dev machine, or any machine that already has it for any
  reason -- Docker Desktop or otherwise), everything below is skipped
  entirely. Only if Docker genuinely doesn't work does this go on to
  enable WSL2's Windows features (possibly requiring a reboot, handled
  via PrepareToInstall/CreateRunOnceEntry below) and then, once those
  features are confirmed active, install Docker Engine inside WSL2. }
function DetectAndInstallPrerequisites(var NeedsRestart: Boolean): Boolean;
var
  RestartedText: String;
begin
  if RestartedFromReboot then
    RestartedText := 'True'
  else
    RestartedText := 'False';
  LogStep('=== DetectAndInstallPrerequisites STARTED (RestartedFromReboot=' + RestartedText + ') ===');
  NeedsRestart := False;

  if RunCommandSilent('docker --version', ExpandConstant('{tmp}')) then
  begin
    LogStep('DetectAndInstallPrerequisites: docker already works, skipping WSL/Docker Engine setup entirely.');
    Result := True;
    Exit;
  end;

  if not RestartedFromReboot then
  begin
    LogStep('DetectAndInstallPrerequisites: docker not found, not yet restarted -- calling InstallWSLFeatures.');
    if not InstallWSLFeatures(NeedsRestart) then
    begin
      LogStep('DetectAndInstallPrerequisites: InstallWSLFeatures returned False -- aborting.');
      Result := False;
      Exit;
    end;

    if NeedsRestart then
    begin
      { The Windows features were just enabled but need a restart
        before they're active -- stop here for now. The actual WSL2
        distro + Docker Engine installation happens on the resumed
        pass below, once those features are genuinely active. }
      LogStep('DetectAndInstallPrerequisites: InstallWSLFeatures says a restart is needed. Stopping here for now.');
      Result := True;
      Exit;
    end;

    { Features were already active, or got enabled without needing a
      restart -- fall through and continue in this same pass, no
      reboot needed. }
    LogStep('DetectAndInstallPrerequisites: InstallWSLFeatures succeeded, no restart needed -- continuing in this same pass.');
  end;

  LogStep('DetectAndInstallPrerequisites: calling InstallDockerInWSL.');
  Result := InstallDockerInWSL;
  if Result then
    LogStep('DetectAndInstallPrerequisites: InstallDockerInWSL returned True')
  else
    LogStep('DetectAndInstallPrerequisites: InstallDockerInWSL returned False');
end;

{ Enables the Hyper-V Windows feature -- Server mode's direct
  equivalent of InstallWSLFeatures, same 3010-means-restart-required
  convention. Local mode never calls this; it has no reason to touch
  Hyper-V at all. }
function InstallHyperVFeature(var NeedsRestart: Boolean): Boolean;
var
  ResultCode: Integer;
  Launched, IsServerOS: Boolean;
begin
  NeedsRestart := False;
  Result := True;

  { Confirmed via a real failure on Windows Server 2025: dism.exe's
    client-oriented enable-feature command reported Hyper-V as
    State=Enabled, but Get-Module -ListAvailable Hyper-V afterward
    came back COMPLETELY EMPTY -- not "present but not loaded," the
    module was never actually deployed to disk at all. That command
    is the Windows 10/11 client convention; Windows Server needs the
    Server Manager route (Install-WindowsFeature -IncludeManagementTools)
    to reliably get the PowerShell module itself deployed, not just
    the role flagged as enabled. Windows 10/11 client editions don't
    have the ServerManager module at all, so they still need the
    dism.exe path -- this has to branch on which OS family it's
    actually running on, not use one command for both. }
  Launched := Exec('powershell.exe', '-Command "exit (Get-CimInstance Win32_OperatingSystem).ProductType"',
    ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  { ProductType: 1 = workstation (Windows 10/11 client), 2 = domain
    controller, 3 = server -- 2 and 3 both mean "use the Server route." }
  IsServerOS := Launched and (ResultCode <> 1);

  if IsServerOS then
  begin
    Launched := Exec('powershell.exe', '-Command "Install-WindowsFeature -Name Hyper-V -IncludeManagementTools"',
      ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if (not Launched) or (ResultCode <> 0) then
    begin
      Result := False;
      Exit;
    end;
  end
  else
  begin
    Launched := Exec('dism.exe', '/online /enable-feature /featurename:Microsoft-Hyper-V /all /norestart', ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if not Launched then
    begin
      Result := False;
      Exit;
    end;
    if ResultCode = 3010 then
      NeedsRestart := True
    else if ResultCode <> 0 then
      Result := False;
  end;

  { Get-WindowsOptionalFeature's own restart signal as a second check,
    regardless of which branch above actually enabled the feature --
    both Install-WindowsFeature and dism.exe share the same underlying
    servicing stack on Server, so this reads correctly either way.

    The real property, CONFIRMED directly from a real system's own
    output rather than assumed, is RestartRequired -- a three-state
    string (No/Possible/Yes), not a plain boolean RestartNeeded the
    way an earlier version of this check wrongly assumed. That earlier
    version was checking a property that doesn't exist on this system
    at all, so it silently never fired. Treating anything other than
    a confirmed "No" as "treat it as needing a restart" is the safer
    direction to be wrong in here -- a needless restart costs a few
    minutes, but proceeding into VM creation on a genuinely
    not-ready Hyper-V is the opaque crash already seen twice now. }
  if Result and (not NeedsRestart) then
  begin
    Launched := Exec('powershell.exe',
      '-Command "$f = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V; if ($f.RestartRequired -ne ''No'') { exit 1 } else { exit 0 }"',
      ExpandConstant('{tmp}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
    if Launched and (ResultCode = 1) then
      NeedsRestart := True;
  end;
end;

{ Creates (or, on a re-run/resume, confirms) Server mode's dedicated
  Hyper-V VM -- the direct structural equivalent of InstallDockerInWSL,
  but the actual work happens in two external PowerShell scripts
  rather than inline here, since VM creation genuinely needs real
  scripting (loops, JSON-ish structured decisions, host resource
  queries) that would be painful to express as a chain of one-line
  Exec calls the way InstallDockerInWSL's bash commands are.

  ExtractTemporaryFile is the confirmed, standard Inno mechanism for
  pulling a Flags: dontcopy file out to the temp folder on demand from
  Pascal code -- needed here specifically because this whole function
  runs during PrepareToInstall, before Inno's normal file-copy step,
  so the app folder doesn't exist yet (the same constraint already
  documented on RunCommandQuiet's WorkingDir parameter elsewhere in
  this file). }
function CreateServerVM: Boolean;
var
  InstallDir, MasterVhdxPath, ScriptParams: String;
begin
  Result := False;
  InstallDir := ExpandConstant('{autopf}\ER-ServiceDesk-VM');
  MasterVhdxPath := InstallDir + '\ubuntu-24.04-master.vhdx';
  LogStep('=== CreateServerVM STARTED, InstallDir=' + InstallDir + ' ===');
  UsedServerVM := True;

  ExtractTemporaryFile('prepare_vm_image.ps1');
  ExtractTemporaryFile('create_server_vm.ps1');

  ScriptParams := '-InstallDir "' + InstallDir + '" -MasterVhdxPath "' + MasterVhdxPath + '"';
  if not RunCommand('Preparing the Server VM image (this can take several minutes the first time)',
    'powershell.exe -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\prepare_vm_image.ps1') + '" ' + ScriptParams,
    ExpandConstant('{tmp}')) then Exit;

  ScriptParams := '-InstallDir "' + InstallDir + '"' +
    ' -VMName "' + VMName + '"' +
    ' -SwitchName "' + VMSwitchName + '"' +
    ' -HostIP "' + VMHostIP + '"' +
    ' -StaticIP "' + VMStaticIP + '"' +
    ' -SubnetPrefixLength "' + VMSubnetPrefixLength + '"' +
    ' -NatSubnetCidr "' + VMNatSubnetCidr + '"' +
    ' -MasterVhdxPath "' + MasterVhdxPath + '"';
  if not RunCommand('Creating the Server VM (this can take several minutes)',
    'powershell.exe -ExecutionPolicy Bypass -File "' + ExpandConstant('{tmp}\create_server_vm.ps1') + '" ' + ScriptParams,
    ExpandConstant('{tmp}')) then Exit;

  { Windows still needs docker.exe/docker-compose.exe on PATH to talk
    to the VM's Docker daemon -- same tools, same reasoning as the
    WSL2 path, just pointed at a different DOCKER_HOST (see
    RunDockerSetup's own Server branch below). }
  if not InstallDockerCLIOnWindows(InstallDir) then Exit;

  if not RunCommand('Configuring Docker connection to the Server VM',
    'setx /M DOCKER_HOST tcp://' + VMStaticIP + ':2375', ExpandConstant('{tmp}')) then Exit;

  Result := True;
end;

{ Server mode's direct equivalent of DetectAndInstallPrerequisites --
  deliberately does NOT skip ahead if "docker --version" already works
  on this machine the way the WSL2 version does. Docker Desktop is
  confirmed unsupported on Windows Server entirely (see the header
  comment at the top of this file), so there's no equivalent
  legitimate "Docker already works here for some other real reason"
  case to skip ahead for on Server the way there is on Local. }
function DetectAndInstallServerPrerequisites(var NeedsRestart: Boolean): Boolean;
var
  RestartedText: String;
begin
  if RestartedFromReboot then
    RestartedText := 'True'
  else
    RestartedText := 'False';
  LogStep('=== DetectAndInstallServerPrerequisites STARTED (RestartedFromReboot=' + RestartedText + ') ===');
  NeedsRestart := False;

  if not RestartedFromReboot then
  begin
    LogStep('DetectAndInstallServerPrerequisites: not yet restarted -- calling InstallHyperVFeature.');
    if not InstallHyperVFeature(NeedsRestart) then
    begin
      LogStep('DetectAndInstallServerPrerequisites: InstallHyperVFeature returned False -- aborting.');
      Result := False;
      Exit;
    end;

    if NeedsRestart then
    begin
      { Same reboot-then-resume shape as the WSL2 path -- Hyper-V
        needs a restart before it's genuinely usable, and the actual
        VM creation happens on the resumed pass below. }
      LogStep('DetectAndInstallServerPrerequisites: InstallHyperVFeature says a restart is needed. Stopping here for now.');
      Result := True;
      Exit;
    end;

    LogStep('DetectAndInstallServerPrerequisites: InstallHyperVFeature succeeded, no restart needed -- continuing in this same pass.');
  end;

  LogStep('DetectAndInstallServerPrerequisites: calling CreateServerVM.');
  Result := CreateServerVM;
  if Result then
    LogStep('DetectAndInstallServerPrerequisites: CreateServerVM returned True')
  else
    LogStep('DetectAndInstallServerPrerequisites: CreateServerVM returned False');
end;

{ Real Inno event function, confirmed via the official
  CodePrepareToInstall.iss example -- runs after the wizard pages but
  before any files get copied, specifically designed for "install
  prerequisites, and handle a mid-install reboot if one turns out to
  be necessary." Skipped entirely for Client mode, which never touches
  Docker/WSL2/Hyper-V at all.

  Local and Server used to share this same call (both went through
  DetectAndInstallPrerequisites) -- confirmed via a real repo audit
  that there was never actually a separate, isolated "Server's WSL2
  path" to swap out cleanly for the Hyper-V VM rework. This branch is
  genuinely new, not a restoration of something that already existed. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  LogStep('=== PrepareToInstall STARTED ===');
  NeedsRestart := False;

  if IsClientMode() then
  begin
    LogStep('PrepareToInstall: Client mode detected, skipping WSL/Docker setup entirely.');
    Result := '';
    Exit;
  end;

  if IsLocalMode() then
  begin
    LogStep('PrepareToInstall: Local mode, calling DetectAndInstallPrerequisites (WSL2).');
    if not DetectAndInstallPrerequisites(NeedsRestart) then
    begin
      Result := 'Setup could not prepare Docker/WSL2 on this machine. ' +
        'Please check that this PC meets the system requirements ' +
        '(Windows 10/11, Windows Server 2022, or Windows Server 2025 ' +
        'with Desktop Experience) and try again.';
      Exit;
    end;

    if NeedsRestart then
    begin
      LogStep('PrepareToInstall: NeedsRestart is True (WSL2), calling CreateRunOnceEntry and returning a non-empty Result.');
      CreateRunOnceEntry;
      Result := 'A required Windows feature (WSL2) was just enabled and ' +
        'needs a restart before Setup can continue.' + #13#13 +
        'After restarting, Setup will automatically resume on its own ' +
        '-- you do not need to run it again yourself.';
      Exit;
    end;
  end
  else if IsServerMode() then
  begin
    LogStep('PrepareToInstall: Server mode, calling DetectAndInstallServerPrerequisites (Hyper-V VM).');
    if not DetectAndInstallServerPrerequisites(NeedsRestart) then
    begin
      Result := 'Setup could not prepare the Server VM on this machine. ' +
        'Please check that this PC meets the system requirements ' +
        '(Windows 10/11, Windows Server 2022, or Windows Server 2025 ' +
        'with Desktop Experience, and Hyper-V support) and try again.';
      Exit;
    end;

    if NeedsRestart then
    begin
      LogStep('PrepareToInstall: NeedsRestart is True (Hyper-V), calling CreateRunOnceEntry and returning a non-empty Result.');
      CreateRunOnceEntry;
      Result := 'A required Windows feature (Hyper-V) was just enabled and ' +
        'needs a restart before Setup can continue.' + #13#13 +
        'After restarting, Setup will automatically resume on its own ' +
        '-- you do not need to run it again yourself.';
      Exit;
    end;
  end;

  Result := '';
end;

{ Builds and starts Docker containers, then runs migrations and seeds
  the database -- skipped for Migration Target, since the real,
  already-migrated data arrives later via pg_restore during the actual
  migration, which brings its own schema with it. Running migrations
  here first would just be redundant work against a database that's
  about to be replaced anyway.

  A real test proved Setup.exe's own process never actually sees the
  PATH/DOCKER_HOST changes InstallDockerInWSL made via setx earlier in
  this same run -- setx only affects processes started afterward, and
  Setup.exe has been running continuously since before those calls.
  Manually running the identical command in a fresh terminal worked
  immediately; from Setup.exe itself it failed every time. Fixed by
  explicitly forcing both values within the same command line that
  runs docker-compose, sidestepping the stale-inherited-environment
  problem entirely rather than depending on inheritance at all -- but
  only when UsedWSL2DockerEngine is actually True, since forcing
  DOCKER_HOST to a TCP address unconditionally would break a machine
  that already has Docker Desktop working correctly via its own named
  pipe connection instead. }
procedure RunDockerSetup;
var
  EnvPrefix, WSLDir, VMDir: String;
  MigrationSucceeded: Boolean;
  MigrationAttempt: Integer;
begin
  { Three real cases, not two -- Setup.exe's own process never picks
    up setx's PATH/DOCKER_HOST changes made earlier in this same run
    (setx only affects future processes, confirmed by real testing),
    so every docker-compose call from Setup.exe itself needs the
    right values forced explicitly, but which values depends on which
    of these three situations this install actually is:

    1. UsedWSL2DockerEngine (Local mode) -- force PATH/DOCKER_HOST at
       WSL2's loopback address, exactly as before.
    2. UsedServerVM (Server mode's new Hyper-V VM) -- force PATH at
       the VM install dir, DOCKER_HOST at the VM's static IP instead.
    3. Neither -- a machine that already had a working Docker for some
       other real reason (Docker Desktop on Local, confirmed still the
       only legitimate case for this, since Server never gets a pass
       on installing its own real Docker the way Local can). Forcing
       DOCKER_HOST unconditionally here would break a Docker Desktop
       connection that already works correctly via its own named
       pipe, not TCP -- so this case forces nothing at all. }
  EnvPrefix := '';
  if UsedWSL2DockerEngine then
  begin
    WSLDir := ExpandConstant('{autopf}\ER-ServiceDesk-WSL');
    EnvPrefix := 'set PATH=%PATH%;' + WSLDir + ';' + WSLDir + '\docker && set DOCKER_HOST=tcp://[::1]:2375 && ';
  end
  else if UsedServerVM then
  begin
    VMDir := ExpandConstant('{autopf}\ER-ServiceDesk-VM');
    EnvPrefix := 'set PATH=%PATH%;' + VMDir + ';' + VMDir + '\docker && set DOCKER_HOST=tcp://' + VMStaticIP + ':2375 && ';
  end;

  { Redirects docker-compose's actual output to a log file -- RunCommand
    itself only captures the exit code, not any real output, and a
    manual run of this exact command (same EnvPrefix, same working
    directory) succeeded completely, meaning whatever's failing here
    is specific to Setup's own automated invocation, not the
    underlying command itself. Same diagnostic technique already
    proven throughout the VM creation debugging -- get the real error
    text instead of guessing from a bare exit code. }
  if not RunCommand('Starting Docker containers',
    EnvPrefix + 'docker-compose up -d --build > "' + ExpandConstant('{app}') + '\docker_compose_log.txt" 2>&1',
    ExpandConstant('{app}')) then
    Exit;

  { Postgres and the API container both need a few seconds to actually
    become ready after starting. This initial pause covers the common
    case; the retry loop below covers the rest. }
  Sleep(20000);

  if IsLocalMode() or IsNewServerSetup() then
  begin
    { A real, recurring failure showed a single fixed wait wasn't
      always enough -- Postgres occasionally takes longer than 20
      seconds to become ready to accept connections, and this used to
      try the migration exactly once, failing outright if that one
      attempt happened to land too early. Retries for up to another
      60 seconds (6 attempts, 10 seconds apart) before giving up for
      real, matching the same retry-with-delay pattern already used
      for the migration worker's own server health check. }
    MigrationSucceeded := False;
    for MigrationAttempt := 1 to 6 do
    begin
      MigrationSucceeded := RunCommandSilent(EnvPrefix + 'docker-compose exec -T api alembic upgrade head', ExpandConstant('{app}'));
      if MigrationSucceeded then
        Break;
      Sleep(10000);
    end;

    if not MigrationSucceeded then
    begin
      if not RunCommand('Running database migrations', EnvPrefix + 'docker-compose exec -T api alembic upgrade head', ExpandConstant('{app}')) then
        Exit;
    end;

    if not RunCommand('Seeding initial data', EnvPrefix + 'docker-compose exec -T api python -m app.db.run_seed', ExpandConstant('{app}')) then
      Exit;
  end;
end;

{ Launches the migration-receiving listener as a detached background
  process -- Migration Target only, and only after RunDockerSetup
  above has already started the containers this listener will later
  need to run docker-compose exec against. Also registers it via a
  Scheduled Task so it survives a reboot before the real migration
  actually arrives, which could be minutes or weeks later. Uses
  ewNoWait for the immediate launch, since this needs to keep running
  indefinitely in the background rather than block Setup's own
  completion. }
procedure StartMigrationListener;
var
  ResultCode: Integer;
begin
  Exec('powershell.exe',
    '-ExecutionPolicy Bypass -File "' + ExpandConstant('{app}\migration_listener.ps1') + '"',
    ExpandConstant('{app}'), SW_HIDE, ewNoWait, ResultCode);

  if not RunCommand('Registering migration listener to survive a reboot',
    'schtasks /create /tn "ER-ServiceDesk-Migration-Listener" /tr "powershell.exe -ExecutionPolicy Bypass -File \"' + ExpandConstant('{app}\migration_listener.ps1') + '\"" /sc onstart /ru SYSTEM /rl HIGHEST /f', ExpandConstant('{tmp}')) then Exit;
  { A real test showed a different Scheduled Task registration using
    this same "quiet" pattern had been silently failing the whole
    time -- the task never actually existed at all, confirmed directly
    via schtasks /query returning "cannot find the file specified."
    Rebooting a server while genuinely waiting for a migration was
    never actually tested until that point, so this exact same,
    previously-invisible failure mode could plausibly have been
    happening here too, undetected. Made visible now for the same
    reason. }
end;

{ Registers env_self_healing.ps1 to run at every Windows startup, as
  SYSTEM (matching every other Scheduled Task this installer creates,
  for the same reason: only SYSTEM or local Administrators have
  sufficient privilege for this kind of unattended, boot-time work).
  Both Server sub-choices, since any Server install has .env and needs
  this resilience. Deliberately only registers the Task for FUTURE
  boots -- doesn't also launch it immediately, since RunDockerSetup
  just above (already run for this same install, moments earlier)
  already did the equivalent work for the current session; running it
  again right now would just be redundant. }
{ RegisterEnvSelfHealing has been removed -- its Scheduled Task is
  fully replaced by server_startup.ps1's own Step 4, which replicates
  the exact same .env recovery logic, now running in guaranteed order
  as part of one consolidated boot sequence instead of as a separate,
  unordered "at startup" task. See SetupServerStartup below. }

{ Opens the Windows Firewall for whatever this Server install actually
  needs to receive from other machines -- a real migration attempt
  timed out (not refused, genuinely no response at all) against a
  fresh Server 2022 install, confirmed via a real test that the
  listener itself was running and correctly listening the whole time,
  pointing squarely at the firewall blocking unsolicited inbound
  connections by default, which fresh Windows Server installs do.

  Port 8000 (the API) for every Server install, since Client mode
  always needs to reach it -- this was never tested before now, and
  would very likely have hit the exact same wall on the very next
  test (a real Client actually connecting) if left unfixed here too.
  Port 8001 (the migration listener) only for Migration Target
  specifically, since New Setup never runs that listener at all --
  opening it there would just be unnecessary exposed surface with no
  real benefit. }
procedure ConfigureFirewallRules;
begin
  if not RunCommand('Configuring firewall for remote connections',
    'netsh advfirewall firewall add rule name="ER-ServiceDesk API" dir=in action=allow protocol=TCP localport=8000', ExpandConstant('{tmp}')) then Exit;

  if IsMigrationTarget() then
    RunCommand('Configuring firewall for migration',
      'netsh advfirewall firewall add rule name="ER-ServiceDesk Migration Listener" dir=in action=allow protocol=TCP localport=8001', ExpandConstant('{tmp}'));

  { Both Server sub-choices, not just Migration Target -- unlike port
    8001, resizing is a feature every Server install has, not just one
    specifically waiting to receive a migration. }
  RunCommand('Configuring firewall for server resource management',
    'netsh advfirewall firewall add rule name="ER-ServiceDesk VM Resize Listener" dir=in action=allow protocol=TCP localport=8002', ExpandConstant('{tmp}'));
end;

{ Launches the VM resource-resize listener as a detached background
  process, and registers it via a Scheduled Task so it survives a
  reboot -- the same two-part launch pattern StartMigrationListener
  uses, but for a listener with no natural end (an admin could resize
  the VM any number of times after install, unlike migration's
  one-shot job), so there's no equivalent "only Migration Target needs
  this" restriction -- both Server sub-choices get it.

  Depends on CreateServerVM having already run (during PrepareToInstall,
  before this point) -- the VM, its static IP, and the per-install SSH
  keypair all need to already exist for this listener's disk-resize
  path to have anything to SSH into. }
procedure StartVmResizeListener;
var
  VMDir, SshKeyPath, ScriptPath, ScriptArgs, WrapperPath, WrapperContent: String;
  ResultCode: Integer;
begin
  VMDir := ExpandConstant('{autopf}\ER-ServiceDesk-VM');
  SshKeyPath := VMDir + '\ssh\id_ed25519';
  ScriptPath := ExpandConstant('{app}\vm_resize_listener.ps1');
  ScriptArgs := '-InstallDir "' + VMDir + '" -VMName "' + VMName + '" -StaticIP "' + VMStaticIP + '" -SshKeyPath "' + SshKeyPath + '"';

  { schtasks' own /TR parameter has a strict, real, documented maximum
    of 261 characters -- confirmed directly via a real failure
    ("Value for '/tr' option cannot be more than 261 character(s)"):
    our full command line, with every argument baked straight into
    the task's run string, blows well past that limit. The standard
    fix is a small wrapper script with the real arguments baked into
    IT instead, so schtasks only ever needs to reference that
    wrapper's short, fixed path -- not the full argument list. All of
    this listener's actual parameter values (VMName, VMStaticIP,
    InstallDir, SshKeyPath) are deterministic constants known at
    install time, not user input, so baking them into a generated file
    is safe and correct, not a workaround that loses information. }
  WrapperPath := ExpandConstant('{app}\run_vm_resize_listener.ps1');
  WrapperContent := '& "' + ScriptPath + '" ' + ScriptArgs;
  SaveStringToFile(WrapperPath, WrapperContent, False);

  Exec('powershell.exe',
    '-ExecutionPolicy Bypass -File "' + WrapperPath + '"',
    ExpandConstant('{app}'), SW_HIDE, ewNoWait, ResultCode);

  RunCommand('Registering VM resize listener to survive a reboot',
    'schtasks /create /tn "ER-ServiceDesk-VM-Resize-Listener" /tr "powershell.exe -ExecutionPolicy Bypass -File \"' + WrapperPath + '\"" /sc onstart /ru SYSTEM /rl HIGHEST /f', ExpandConstant('{tmp}'));
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsClientMode() then
    begin
      WriteEnvFiles;
      RunDockerSetup;
      if IsMigrationTarget() then
        StartMigrationListener;
      if IsServerMode() then
      begin
        { SetupWslPortForward and RegisterServerStartupTask are both
          gone -- the VM's own static IP (set up as part of
          CreateServerVM, during PrepareToInstall, before this point)
          replaces the old per-boot WSL2 IP-forwarding dance entirely,
          and AutomaticStartAction Start + Docker's own restart:
          unless-stopped replace the whole reason a Windows Service
          existed to babysit anything at boot. Only the firewall rule
          is still genuinely needed here -- that's about Windows'
          OWN inbound traffic, unrelated to what's hosting Docker
          behind it. }
        ConfigureFirewallRules;
        StartVmResizeListener;
      end;
    end;
    WriteRegistryValues;
  end;
end;

{ Displays Migration Target's one-time token on Inno's built-in
  Finished page.

  A real test showed the first attempt at this -- setting a much
  longer, multi-paragraph WizardForm.FinishedLabel.Caption -- got
  silently clipped mid-sentence, with the token never visible at all.
  FinishedLabel is sized for a short, single message; it doesn't wrap
  or scroll longer text. Fixed by keeping the label short (matching
  roughly what the default, unmodified message's length already
  displayed correctly) and adding a separate, properly-sized TNewMemo
  control -- the same control class Inno's own built-in Ready page
  already uses internally, confirmed directly against jrsoftware.org's
  official Support Classes Reference -- to hold the token itself.
  ReadOnly, so it can't be edited, but text inside a memo is trivially
  selectable/copyable, which is genuinely better for a secret token
  than a plain label would have been anyway.

  Parented to WizardForm.FinishedLabel.Parent rather than a guessed
  WizardForm.FinishedPage property name -- same actual container
  either way, but sourced from a property already proven to exist
  (FinishedLabel itself), not one assumed by naming-convention pattern.

  By this point WriteEnvFiles has already run (during ssPostInstall,
  which completes before the wizard ever reaches this page), so
  MigrationTargetToken is already populated. Every other mode gets
  Inno's normal, unmodified Finished page. }
procedure CurPageChanged(CurPageID: Integer);
begin
  if (CurPageID = wpFinished) and IsMigrationTarget() then
  begin
    WizardForm.FinishedLabel.Caption :=
      'Setup has finished installing ER-ServiceDesk in Migration Target mode.' + #13#10 +
      'Copy the migration token below now -- it will not be shown again.';

    if MigrationTokenMemo = nil then
    begin
      MigrationTokenMemo := TNewMemo.Create(WizardForm);
      MigrationTokenMemo.Parent := WizardForm.FinishedLabel.Parent;
      MigrationTokenMemo.Left := WizardForm.FinishedLabel.Left;
      MigrationTokenMemo.Top := WizardForm.FinishedLabel.Top + WizardForm.FinishedLabel.Height + 16;
      MigrationTokenMemo.Width := WizardForm.FinishedLabel.Width;
      MigrationTokenMemo.Height := 40;
      MigrationTokenMemo.ReadOnly := True;
    end;
    MigrationTokenMemo.Lines.Text := MigrationTargetToken;
    MigrationTokenMemo.Visible := True;
  end;
end;

{ Cleans up the two things this installer writes outside of Inno's own
  automatic tracking (.env's backup copy and the deployment registry
  values) -- Inno's uninstaller only auto-removes things declared in
  the Files, Dirs, or Registry sections, not anything written
  imperatively via Pascal code like SaveStringToFile/ForceDirectories/
  RegWriteStringValue, so this has to be done explicitly.

  Deliberately scoped to just the backup folder and the 'deployment'
  registry subkey specifically -- not the whole ER-ServiceDesk registry
  tree, which also holds harmless preferences (theme, window geometry)
  that have no reason to be wiped on an ordinary uninstall. The backup
  folder and deployment values are different: they hold live secrets
  (the Postgres password, SECRET_KEY, Gmail app password) that protect
  nothing once the app itself is gone, so leaving them behind would be
  a liability, not a convenience. }
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DelTree(ExpandConstant('{autopf}\ER-ServiceDesk-Backup'), True, True, True);
    RegDeleteKeyIncludingSubkeys(HKEY_LOCAL_MACHINE, RegPath);
  end;
end;
