; ER-ServiceDesk-Installer/setup.iss
;
; STEP 8. Steps 1-7 are now fully tested end to end on real hardware for
; all four real scenarios, including Start Menu/desktop shortcuts
; (confirmed created correctly, and correctly removed on uninstall).
;
; This step moves the install location from %LOCALAPPDATA% (per-user)
; to Program Files (machine-wide), and PrivilegesRequired from lowest
; to admin. This wasn't an arbitrary change -- it resolves a real
; mismatch: business software is typically installed once by whoever
; has admin rights, but may be used afterward by a different employee
; logging into that same PC. A per-user location tied to whichever
; account happened to run the installer would be invisible to anyone
; else logging in; Program Files is visible to every account on the
; machine regardless of who set it up.
;
; {autopf} confirmed directly against jrsoftware.org's own official
; Directory Constants documentation as their explicitly recommended
; constant for this (auto-resolves correctly based on privilege mode).
;
; This required matching changes on the desktop app side too --
; desktop/app_paths.py now resolves to Program Files instead of
; LOCALAPPDATA, and desktop/settings_manager.py now splits its
; registry writes: theme stays per-user (HKEY_CURRENT_USER, a genuine
; per-person preference), while install_mode/backend_url/business_name
; move to machine-wide (HKEY_LOCAL_MACHINE, facts about the machine's
; setup, not about whoever's logged in) -- confirmed via real
; functional tests on both files, not just reasoned through.
;
; The registry writes/deletes below also moved from HKEY_CURRENT_USER
; to HKEY_LOCAL_MACHINE to match. Writing to HKEY_LOCAL_MACHINE
; requires admin rights, which this installer now has by design.
;
; Still unverified from this end -- Inno Setup produces a real Windows
; executable installer, and there's no way to test that outside a real
; Windows machine. The real proof is running it and reporting back
; exactly what happens.

[Setup]
AppName=ER-ServiceDesk
AppVersion=1.1.1
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

var
  ModePage: TInputOptionWizardPage;
  ServerSubChoicePage: TInputOptionWizardPage;
  CredentialsPage: TInputQueryWizardPage;
  ClientAddressPage: TInputQueryWizardPage;
  MigrationTargetToken: String;
  MigrationTokenMemo: TNewMemo;

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

  ServerSubChoicePage := CreateInputOptionPage(ModePage.ID,
    'Server Setup Type',
    'Is this a brand new server, or the target of a migration from an existing Local install?',
    'This page only appears because Server was selected. Select one of the following options, then click Next to continue.',
    True, False);
  ServerSubChoicePage.Add('New Setup -- set up a brand new server from scratch');
  ServerSubChoicePage.Add('Migration Target -- this server will receive data migrated from an existing Local install');
  ServerSubChoicePage.SelectedValueIndex := 0;

  { Gmail credentials + business name. Only shown for Local and
    Server -> New Setup, via ShouldSkipPage below. }
  CredentialsPage := CreateInputQueryPage(ServerSubChoicePage.ID,
    'Email & Business Details',
    'This information is used to send email notifications to customers.',
    'Enter your Gmail address, its App Password (not your regular Gmail password), and your business name.');
  CredentialsPage.Add('Gmail Address:', False);
  CredentialsPage.Add('Gmail App Password:', True);
  CredentialsPage.Add('Business Name:', False);

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

{ Runs a command via cmd.exe (so PATH-based tool resolution works the
  same as typing it in a real command prompt), waits for it to finish,
  and shows a clear error naming exactly what failed and what command
  to try manually if it did -- rather than leaving someone with a
  silently half-configured install and no idea why. }
function RunCommand(const Description, Params: String): Boolean;
var
  ResultCode: Integer;
begin
  Result := Exec('cmd.exe', '/C ' + Params, ExpandConstant('{app}'), SW_HIDE, ewWaitUntilTerminated, ResultCode);
  if Result then
    Result := ResultCode = 0;
  if not Result then
    MsgBox('Setup step failed: ' + Description + #13#13 +
      'ER-ServiceDesk is installed at ' + ExpandConstant('{app}') + '. ' +
      'You may be able to fix this by running the following manually ' +
      'from that folder:' + #13#13 + Params, mbError, MB_OK);
end;

{ Builds and starts Docker containers, then runs migrations and seeds
  the database -- skipped for Migration Target, since the real,
  already-migrated data arrives later via pg_restore during the actual
  migration, which brings its own schema with it. Running migrations
  here first would just be redundant work against a database that's
  about to be replaced anyway. }
procedure RunDockerSetup;
begin
  if not RunCommand('Starting Docker containers', 'docker-compose up -d --build') then
    Exit;

  { Postgres and the API container both need a few seconds to actually
    become ready after starting. A fixed pause is simple and pragmatic
    here; a more precise health-check retry loop (matching what the
    desktop app's own BackendStartupWorker already does) is a
    reasonable future improvement, not required for this to work. }
  Sleep(20000);

  if IsLocalMode() or IsNewServerSetup() then
  begin
    if not RunCommand('Running database migrations', 'docker-compose exec -T api alembic upgrade head') then
      Exit;
    if not RunCommand('Seeding initial data', 'docker-compose exec -T api python -m app.db.run_seed') then
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
