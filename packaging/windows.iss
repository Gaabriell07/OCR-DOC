#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#define SourceRoot AddBackslash(SourcePath) + ".."

[Setup]
AppId=OCRDOC.Local.Windows
AppName=OCR DOC
AppVersion={#AppVersion}
DefaultDirName={localappdata}\Programs\OCR DOC
DefaultGroupName=OCR DOC
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir={#SourceRoot}\dist\installer
OutputBaseFilename=OCR-DOC-Setup-{#AppVersion}-windows-x64
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\OCR-DOC.exe
CloseApplications=yes

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "{#SourceRoot}\dist\OCR-DOC\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\OCR DOC"; Filename: "{app}\OCR-DOC.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\OCR DOC"; Filename: "{app}\OCR-DOC.exe"; WorkingDir: "{app}"

[Run]
Filename: "{app}\OCR-DOC.exe"; Description: "Abrir OCR DOC"; Flags: nowait postinstall skipifsilent
