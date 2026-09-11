#define MyAppName      "Video Maker Pro"
#define MyAppVersion   "8.3.1"
#define MyAppExeName   "VideoMakerPro.exe"

[Setup]
AppId={{8A3F2E1D-4B5C-4F6E-9A2B-1C3D5E7F8A9B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=VideoMakerPro_Setup
SetupIconFile=app_icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
MinVersion=10.0
CloseApplications=force
CloseApplicationsFilter=*VideoMakerPro*
RestartApplications=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Sozdatj yarlik na rabochem stole"

[Files]
Source: "dist\VideoMakerPro.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Udalitj {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Zapustitj {#MyAppName}"; Flags: nowait postinstall runasoriginaluser
