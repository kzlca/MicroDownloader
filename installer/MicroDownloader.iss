; Micro Downloader: polished per-user Windows installer. Inno Setup >= 6.6 recommended.
; Run after the PyInstaller onedir build with scripts/build_release.py --mode installer.
#include "version.iss"
#define AppName "Micro Downloader"
#define MainExe "MicroDownloader.exe"

[Setup]
AppId={{E7C09717-8A6D-43D1-9F25-76A89E223F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=kzlca
AppComments=Download manager and verified missing-byte recovery
AppPublisherURL=https://github.com/kzlca/MicroDownloader
AppSupportURL=https://github.com/kzlca/MicroDownloader/issues
AppUpdatesURL=https://github.com/kzlca/MicroDownloader/releases
DefaultDirName={localappdata}\Programs\Micro Downloader
DefaultGroupName=Micro Downloader
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
WizardStyle=modern dynamic
WizardSizePercent=110,110
WizardImageFile=assets\wizard-side.bmp
WizardSmallImageFile=assets\wizard-small.bmp
SetupIconFile=..\micro_downloader\assets\logo.ico
UninstallDisplayIcon={app}\{#MainExe}
UninstallDisplayName=Micro Downloader
OutputDir=..\release
OutputBaseFilename=MicroDownloader-{#AppVersion}-windows-x64-Setup
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=yes
RestartApplications=no
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=..\LICENSE

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "turkish"; MessagesFile: "compiler:Languages\Turkish.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "..\dist\MicroDownloader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Micro Downloader"; Filename: "{app}\{#MainExe}"; IconFilename: "{app}\{#MainExe}"; Comment: "Download manager and recovery tools"
Name: "{autodesktop}\Micro Downloader"; Filename: "{app}\{#MainExe}"; IconFilename: "{app}\{#MainExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MainExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

; User data is intentionally not removed by the uninstaller:
; %LOCALAPPDATA%\MicroDownloader\micro-downloader.db stores download URLs and progress.
