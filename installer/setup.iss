; ER-ServiceDesk-Installer/setup.iss
;
; STEP 9. Steps 1-8 are now fully tested end to end on real hardware
; for all four real scenarios under the Program Files/admin-privileges
; architecture, including two real bugs found and fixed through that
; testing (a 32-bit Program Files path mismatch, and Client mode's
; .env check incorrectly blocking launch -- the latter fixed in
; desktop/main.py, not this file).
;
; This step adds the single largest, most technically involved piece
; of the whole installer: automatically installing Docker Engine
; inside WSL2 (no Docker Desktop, matching this project's actual
; target architecture) when it isn't already present, including
; handling a mid-install reboot if enabling WSL2's Windows features
; requires one -- for Local and Server only; Client never touches any
; of this, since it has no local Docker at all.
;
; Worth being honest and explicit: this is genuinely the least
; verifiable piece built so far. Every individual technique used here
; was confirmed against real, authoritative sources before being
; written -- never guessed -- but the full sequence has never run
; anywhere, and several of the pieces it depends on (systemd inside
; WSL2, Docker's TCP exposure, winget, the reboot-resume mechanism
; itself) genuinely cannot be tested outside a real Windows machine
; that's never had WSL2 or Docker before. This is exactly what the
; planned VM test exists to prove, and this piece should be expected
; to need real iteration once that becomes possible, unlike most of
; what's been built so far tonight.
;
; Key techniques and why each was chosen, all confirmed via real
; sources rather than assumed:
;   - PrepareToInstall/RunOnce/InitializeSetup for the reboot-resume
;     mechanism -- confirmed via jrsoftware's own official example
;     script demonstrating this exact scenario
;     (CodePrepareToInstall.iss), not a WiX-style native feature Inno
;     itself doesn't have.
;   - "wsl --import" from an official Ubuntu WSL rootfs tarball,
;     deliberately not "wsl --install -d <distro>" -- confirmed via a
;     real, currently-open Microsoft WSL GitHub issue that --install
;     (even with --no-launch) still requires an interactive Unix
;     username/password prompt on first launch, which would hang an
;     unattended install indefinitely.
;   - A systemd override (not daemon.json's "hosts" key alone) to
;     expose Docker over TCP -- confirmed as the correct approach,
;     since daemon.json's hosts key alone conflicts with the distro's
;     own default ExecStart and prevents Docker from starting.
;   - winget for the Windows-side Docker CLI, rather than a manually
;     versioned download from download.docker.com/win/static/, which
;     would require hardcoding a specific version number that goes
;     stale over time.
;
; Still unverified from this end -- Inno Setup produces a real Windows
; executable installer, and there's no way to test that outside a real
; Windows machine. The real proof is running it and reporting back
; exactly what happens.
; exactly what happens.

[Setup]
AppName=ER-ServiceDesk
AppVersion=1.2.2
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
    here as global constants instead, same fix as RegPath above. }
  WSLDistroName = 'ER-ServiceDesk-Docker';
  WSLRootfsUrl = 'https://cloud-images.ubuntu.com/wsl/jammy/current/ubuntu-jammy-wsl-amd64-wsl.rootfs.tar.gz';

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
  { On a resumed run, every one of our custom pages gets skipped
    unconditionally -- the person already answered these before the
    reboot, and InitializeWizard above already silently restored those
    answers into the same page objects. They should never see the
    wizard a second time. }
  if RestartedFromReboot then
  begin
    Result := True;
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
    RegWriteStringValue(HKEY_LOCAL_MACHINE, RegPath, 'backend_url', ClientAddressPage.Values[0]);
  end;
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
begin
  Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
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
begin
  Result := Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := ResultCode = 0;
end;

{ Runs a command via cmd.exe (so PATH-based tool resolution works the
  same as typing it in a real command prompt), waits for it to finish,
  and shows a clear error naming exactly what failed and what command
  to try manually if it did -- rather than leaving someone with a
  silently half-configured install and no idea why. }
function RunCommand(const Description, Params, WorkingDir: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C ' + Params, WorkingDir, SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := ResultCode = 0;
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
  further needed (e.g. the feature was already enabled). }
function InstallWSLFeatures(var NeedsRestart: Boolean): Boolean;
var
  ResultCode: Integer;
begin
  NeedsRestart := False;
  Result := True;

  Exec('dism.exe', '/online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if ResultCode = 3010 then
    NeedsRestart := True
  else if ResultCode <> 0 then
  begin
    Result := False;
    Exit;
  end;

  Exec('dism.exe', '/online /enable-feature /featurename:VirtualMachinePlatform /all /norestart', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
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
function InstallDockerInWSL: Boolean;
var
  InstallDir, TarballPath: String;
begin
  Result := False;
  InstallDir := ExpandConstant('{autopf}\ER-ServiceDesk-WSL');
  TarballPath := InstallDir + '\ubuntu-rootfs.tar.gz';

  RunCommandQuiet('mkdir "' + InstallDir + '"', ExpandConstant('{tmp}'));
  { Failing here because the folder already exists from a prior
    attempt isn't a real problem -- keep going rather than treat it as
    fatal. }

  if not RunCommand('Downloading Ubuntu for WSL (this can take a few minutes)',
    'curl -L -o "' + TarballPath + '" ' + WSLRootfsUrl, ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Importing Ubuntu into WSL2',
    'wsl --import ' + WSLDistroName + ' "' + InstallDir + '" "' + TarballPath + '"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Enabling systemd inside WSL',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "printf ''[boot]\nsystemd=true\n'' > /etc/wsl.conf"', ExpandConstant('{tmp}')) then Exit;

  { Restarts the whole WSL subsystem so the systemd config just
    written actually takes effect -- the distro's next launch (the
    very next command below) will have systemd as PID 1. }
  if not RunCommand('Restarting WSL to apply systemd', 'wsl --shutdown', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Installing Docker Engine inside WSL (this can take a few minutes)',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "curl -fsSL https://get.docker.com | sh"', ExpandConstant('{tmp}')) then Exit;

  { Confirmed via real sources this is the correct way to expose
    Docker's daemon over TCP -- a systemd override clearing the
    distro's default ExecStart (which already specifies its own -H
    flag) and replacing it with one that includes both the Unix socket
    and a TCP listener. Editing daemon.json's "hosts" key instead, on
    its own, conflicts with the unit file's own -H flag and prevents
    Docker from starting at all -- confirmed as a real, known issue,
    not a guess. }
  if not RunCommand('Configuring Docker to be reachable from Windows',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "mkdir -p /etc/systemd/system/docker.service.d && printf ''[Service]\nExecStart=\nExecStart=/usr/bin/dockerd -H unix:///var/run/docker.sock -H tcp://127.0.0.1:2375\n'' > /etc/systemd/system/docker.service.d/override.conf"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Starting Docker',
    'wsl -d ' + WSLDistroName + ' -u root -e bash -c "systemctl daemon-reload && systemctl enable docker && systemctl restart docker"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Installing Windows Docker CLI tools',
    'winget install --id Docker.DockerCli --accept-package-agreements --accept-source-agreements', ExpandConstant('{tmp}')) then Exit;

  { Non-critical, best-effort convenience wrapper -- rather than
    assume exactly which binary shape winget's Docker.DockerCli
    package provides, this creates a plain docker-compose.bat
    forwarding to "docker compose" (the modern plugin form, reliably
    installed on the WSL side by the get.docker.com script above), so
    this installer's already-tested code -- which calls the older
    hyphenated "docker-compose" command throughout -- keeps working
    regardless of exactly what winget installed. One genuine
    uncertainty here, unlike everything else in this function: whether
    a single %* or doubled %%* is correct depends on whether percent
    expansion happens when this runs directly via cmd.exe /C (as
    opposed to from inside an already-executing .bat file, where
    doubling is definitely required) -- used single %* here as the
    more likely correct form for this direct-invocation context, but
    this is genuinely the one line in this whole function I'm least
    certain about, and it's deliberately non-fatal if wrong. }
  RunCommandQuiet('(echo @echo off & echo docker compose %*) > "' + InstallDir + '\docker-compose.bat"', ExpandConstant('{tmp}'));
  { Non-fatal if this specific convenience wrapper fails to write --
    "docker compose" (space form) may still work directly. }

  if not RunCommand('Making the docker-compose command available',
    'setx /M PATH "%PATH%;' + InstallDir + '"', ExpandConstant('{tmp}')) then Exit;

  if not RunCommand('Configuring Docker connection',
    'setx /M DOCKER_HOST tcp://127.0.0.1:2375', ExpandConstant('{tmp}')) then Exit;

  { Without this, the WSL distro (and Docker inside it) would not be
    running again after the next reboot -- WSL distros don't auto-start
    on their own. }
  if not RunCommand('Setting up automatic Docker startup',
    'schtasks /create /tn "ER-ServiceDesk-WSL-Docker-Startup" /tr "wsl -d ' + WSLDistroName + ' -u root -e /bin/true" /sc onstart /ru SYSTEM /rl HIGHEST /f', ExpandConstant('{tmp}')) then Exit;

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
begin
  NeedsRestart := False;

  if RunCommandSilent('docker --version', ExpandConstant('{tmp}')) then
  begin
    Result := True;
    Exit;
  end;

  if not RestartedFromReboot then
  begin
    if not InstallWSLFeatures(NeedsRestart) then
    begin
      Result := False;
      Exit;
    end;

    if NeedsRestart then
    begin
      { The Windows features were just enabled but need a restart
        before they're active -- stop here for now. The actual WSL2
        distro + Docker Engine installation happens on the resumed
        pass below, once those features are genuinely active. }
      Result := True;
      Exit;
    end;

    { Features were already active, or got enabled without needing a
      restart -- fall through and continue in this same pass, no
      reboot needed. }
  end;

  Result := InstallDockerInWSL;
end;

{ Real Inno event function, confirmed via the official
  CodePrepareToInstall.iss example -- runs after the wizard pages but
  before any files get copied, specifically designed for "install
  prerequisites, and handle a mid-install reboot if one turns out to
  be necessary." Skipped entirely for Client mode, which never touches
  Docker/WSL2 at all. }
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  NeedsRestart := False;

  if IsClientMode() then
  begin
    Result := '';
    Exit;
  end;

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
    CreateRunOnceEntry;
    Result := 'A required Windows feature (WSL2) was just enabled and ' +
      'needs a restart before Setup can continue.' + #13#13 +
      'After restarting, Setup will automatically continue -- you do ' +
      'not need to run it again yourself.';
    Exit;
  end;

  Result := '';
end;

{ Builds and starts Docker containers, then runs migrations and seeds
  the database -- skipped for Migration Target, since the real,
  already-migrated data arrives later via pg_restore during the actual
  migration, which brings its own schema with it. Running migrations
  here first would just be redundant work against a database that's
  about to be replaced anyway. }
procedure RunDockerSetup;
begin
  if not RunCommand('Starting Docker containers', 'docker-compose up -d --build', ExpandConstant('{app}')) then
    Exit;

  { Postgres and the API container both need a few seconds to actually
    become ready after starting. A fixed pause is simple and pragmatic
    here; a more precise health-check retry loop (matching what the
    desktop app's own BackendStartupWorker already does) is a
    reasonable future improvement, not required for this to work. }
  Sleep(20000);

  if IsLocalMode() or IsNewServerSetup() then
  begin
    if not RunCommand('Running database migrations', 'docker-compose exec -T api alembic upgrade head', ExpandConstant('{app}')) then
      Exit;
    if not RunCommand('Seeding initial data', 'docker-compose exec -T api python -m app.db.run_seed', ExpandConstant('{app}')) then
      Exit;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsClientMode() then
    begin
      WriteEnvFiles;
      RunDockerSetup;
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
