; ER-ServiceDesk-Installer/setup.iss
;
; STEP 4. Steps 1-3 proved the toolchain, mode selection, and Server
; sub-choice screen all work end to end -- confirmed on a real machine
; for all scenarios independently.
;
; This step adds the real substance: collecting Gmail credentials and
; a business name (Local and Server -> New Setup only; skipped for
; Server -> Migration Target, since that data arrives later via
; migration itself, and skipped for Client, which owns neither), a
; server address field (Client only), auto-generating SECRET_KEY and
; a Postgres password, and writing the real .env file -- to both the
; main install location and the separate backup folder -- plus the
; Windows Registry values (install_mode, backend_url, business_name)
; that the desktop app's settings_manager.py reads on every launch.
;
; Every piece of syntax here was verified directly against jrsoftware.org's
; own official documentation or real example scripts before being written --
; CreateInputQueryPage and its Password-masking parameter, SaveStringToFile,
; ForceDirectories, Random, and RegWriteStringValue with HKEY_CURRENT_USER.
; An earlier attempt included a Randomize call to seed Random() -- that's
; not a real function here, confirmed directly against jrsoftware.org's
; complete official Support Functions Reference, which lists every function
; this environment exposes and Randomize isn't among them. Removed; that
; same reference's own entry for Random() doesn't mention any seeding
; requirement either, unlike generic Pascal tutorials, so it's very likely
; auto-seeded internally.
;
; Still unverified from this end -- Inno Setup produces a real Windows
; executable installer, and there's no way to test that outside a real
; Windows machine. The real proof is running it and reporting back
; exactly what happens.

[Setup]
AppName=ER-ServiceDesk
AppVersion=1.0.4
DefaultDirName={localappdata}\ER-ServiceDesk
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=.
OutputBaseFilename=ER-ServiceDesk-Setup

[Files]
Source: "test-install-proof.txt"; DestDir: "{app}"
Source: "local-mode-marker.txt"; DestDir: "{app}"; Check: IsLocalMode
Source: "server-mode-marker.txt"; DestDir: "{app}"; Check: IsServerMode
Source: "client-mode-marker.txt"; DestDir: "{app}"; Check: IsClientMode
Source: "server-new-setup-marker.txt"; DestDir: "{app}"; Check: IsNewServerSetup
Source: "server-migration-target-marker.txt"; DestDir: "{app}"; Check: IsMigrationTarget

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

  SaveStringToFile(ExpandConstant('{app}\.env'), EnvContent, False);

  BackupDir := ExpandConstant('{localappdata}\ER-ServiceDesk-Backup');
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
    RegWriteStringValue(HKEY_CURRENT_USER, RegPath, 'install_mode', 'local');
    RegWriteStringValue(HKEY_CURRENT_USER, RegPath, 'backend_url', 'http://localhost:8000');
    RegWriteStringValue(HKEY_CURRENT_USER, RegPath, 'business_name', CredentialsPage.Values[2]);
  end
  else if IsClientMode() then
  begin
    RegWriteStringValue(HKEY_CURRENT_USER, RegPath, 'install_mode', 'client');
    RegWriteStringValue(HKEY_CURRENT_USER, RegPath, 'backend_url', ClientAddressPage.Values[0]);
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    if not IsClientMode() then
      WriteEnvFiles;
    WriteRegistryValues;
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
    DelTree(ExpandConstant('{localappdata}\ER-ServiceDesk-Backup'), True, True, True);
    RegDeleteKeyIncludingSubkeys(HKEY_CURRENT_USER, RegPath);
  end;
end;
