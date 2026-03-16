; Finelly Windows installer (requires Docker Desktop already installed)
; Build from installer with: iscc verbiage.iss

#define MyAppName "Finelly"
#define MyAppVersion "1.0"
#define MyAppPublisher "Finelly"
#define MyAppURL "https://github.com/"

[Setup]
AppId={{B7E8F2A1-4C3D-4E9F-8A2B-1D5E6F7A8B9C}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=output
OutputBaseFilename=FinellySetup
Compression=lzma2
SolidCompression=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Create a &Quick Launch icon"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Copy entire app folder (parent of installer). Exclude secrets and dev cruft.
Source: "..\*"; DestDir: "{app}"; Flags: recursesubdirs skipifsourcedoesntexist ignoreversion; Excludes: ".env;.git;*__pycache__*;.venv;*.pyc;.DS_Store;installer"

[Dirs]
; Ensure app can write data (Docker volumes live outside this dir, but SQLite etc. may be used if run without Docker)
Permissions: users-full

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\Start.bat"; WorkingDir: "{app}"; Comment: "Start Finelly (Docker)"
Name: "{group}\Stop Finelly"; Filename: "cmd.exe"; Parameters: "/c docker compose down"; WorkingDir: "{app}"; Comment: "Stop Finelly containers"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\Start.bat"; WorkingDir: "{app}"; Tasks: desktopicon; Comment: "Start Finelly (Docker)"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\Start.bat"; WorkingDir: "{app}"; Tasks: quicklaunchicon

[Run]
; Optional: run Finelly after install
Filename: "{app}\Start.bat"; Description: "Start {#MyAppName} now"; WorkingDir: "{app}"; Flags: postinstall nowait skipifsilent

[UninstallDelete]
Type: dirifempty; Name: "{app}"

[Messages]
WelcomeLabel2=This will install [name] on your computer.%n%nDocker Desktop must already be installed and running. If it is not, please install it first from docker.com.
