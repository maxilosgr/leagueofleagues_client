; League of Leagues Installer Script
; Created with Inno Setup Compiler

#define MyAppName "League of Leagues"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Gregorios Machairidis"
#define MyAppURL "https://gameras.gr/"
#define MyAppExeName "LeagueOfLeagues.exe"
#define MyAppAssocName MyAppName + " File"
#define MyAppAssocExt ".lol"
#define MyAppAssocKey StringChange(MyAppAssocName, " ", "") + MyAppAssocExt

[Setup]
; NOTE: The value of AppId uniquely identifies this application. Do not use the same AppId value in installers for other applications.
AppId={{B6C0565F-32B1-485D-B07A-F2ADD1BD7C0A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Uncomment the following line to run in non administrative install mode (install for current user only.)
;PrivilegesRequired=lowest
OutputDir=.\Output
OutputBaseFilename=LeagueOfLeaguesSetup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
; Ask to close the application if it's running
CloseApplications=yes
; Always restart applications after installation (better for automatic updates)
RestartApplications=yes
; Set a warning if application is running
CloseApplicationsFilter=*{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checkedonce
Name: "startup"; Description: "Start {#MyAppName} when Windows starts"; GroupDescription: "Startup options:"

[Files]
Source: "{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
; Add additional files or folders here if needed
Source: "icon.ico"; DestDir: "{app}"; Flags: ignoreversion
; If your application has additional files or directories, add them below:
;Source: ".\dist\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon
; Create a startup entry if selected
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: startup

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: shellexec nowait skipifsilent runasoriginaluser

[Registry]
; Add application to Programs and Features list
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayName"; ValueData: "{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "UninstallString"; ValueData: """{app}\unins000.exe"""; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "QuietUninstallString"; ValueData: """{app}\unins000.exe"" /SILENT"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "InstallLocation"; ValueData: "{app}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "Publisher"; ValueData: "{#MyAppPublisher}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "URLInfoAbout"; ValueData: "{#MyAppURL}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayVersion"; ValueData: "{#MyAppVersion}"; Flags: uninsdeletekey
; Add startup entry to registry (alternative to .lnk file in Startup folder)
Root: HKCU; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#MyAppName}"; ValueData: """{app}\{#MyAppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Code]
// Custom code for checking if the app is running and asking to close it

// Check if process is running via window class
function FindWindowByClassName(const ClassName: string): HWND;
external 'FindWindowA@user32.dll stdcall';

// Check if process is running via window title
function FindWindowByWindowName(const WindowName: string): HWND;
external 'FindWindowA@user32.dll stdcall';

// Check if application is running by looking for its main window
function IsAppRunning(): Boolean;
var
  AppWindow: HWND;
begin
  Result := False;
  
  // Try to find the window by various methods
  AppWindow := FindWindowByWindowName('{#MyAppName}');
  if AppWindow <> 0 then
  begin
    Result := True;
    Exit;
  end;
  
  // You can add other window name variations here
  AppWindow := FindWindowByWindowName('League of Leagues');
  if AppWindow <> 0 then
  begin
    Result := True;
    Exit;
  end;
  
  // Additionally, check by class name (common for applications)
  AppWindow := FindWindowByClassName('LeagueOfLeagues');
  if AppWindow <> 0 then
  begin
    Result := True;
    Exit;
  end;
  
  // Try other variations of class names
  AppWindow := FindWindowByClassName('LeagueOfLeaguesMain');
  if AppWindow <> 0 then
  begin
    Result := True;
  end;
end;

// Check if the app is running using a more reliable method that doesn't use unavailable functions
function CheckAppRunning(const FileName: string): Boolean;
var
  ResultCode: Integer;
  ProcessFound: Boolean;
  TaskListOutput: AnsiString; // Changed from string to AnsiString
  TempFile: string;
begin
  Result := False;
  
  // First try the window detection methodA
  Result := IsAppRunning();
  if Result then
    Exit; // App was found running
    
  // Fall back to using tasklist command (more reliable)
  TempFile := ExpandConstant('{tmp}\tasklist.txt');
  if Exec('cmd.exe', '/c tasklist /FI "IMAGENAME eq ' + ExtractFileName(FileName) + '" /NH > "' + TempFile + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
  begin
    // Make sure to properly initialize the variable before loading
    TaskListOutput := '';
    
    if LoadStringFromFile(TempFile, TaskListOutput) then
    begin
      // If the process is found, the output contains the EXE name
      ProcessFound := Pos(ExtractFileName(FileName), String(TaskListOutput)) > 0;
      Result := ProcessFound;
    end;
  end;
  
  // Clean up the temp file
  DeleteFile(TempFile);
end;




// Try to close the application gracefully
procedure TerminateApp(const FileName: string);
var
  ResultCode: Integer;
begin
  // Use taskkill to terminate the process
  Exec('taskkill.exe', '/F /IM ' + ExtractFileName(FileName), '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  // Give it a moment to close
  Sleep(1500);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  Log('InitializeSetup started');
  
  try
    // Just log some basic information
    Log('Checking for previous installation...');
    if RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1') then
    begin
      Log('Found previous installation registry key');
    end else
    begin
      Log('No previous installation registry key found');
    end;
    
    // Log system paths
    Log('Temp directory: ' + ExpandConstant('{tmp}'));
    Log('Windows directory: ' + ExpandConstant('{win}'));
    Log('System directory: ' + ExpandConstant('{sys}'));
    
  except
    // Note: No "on E: Exception do" here - just plain "except"
    Log('Error in InitializeSetup: ' + GetExceptionMessage);
    Result := False;
  end;
  
  if Result then
    Log('InitializeSetup completed with result: True')
  else
    Log('InitializeSetup completed with result: False');
end;

// Custom code for a more interactive installation
procedure InitializeWizard;
var
  LogoImage: TBitmapImage;
  LogoFilePath: String;
begin
  // Create a logo image on the wizard form if the file exists
  LogoFilePath := ExpandConstant('{tmp}\installer_logo.bmp');
  if FileExists(LogoFilePath) then
  begin
    LogoImage := TBitmapImage.Create(WizardForm);
    LogoImage.Parent := WizardForm;
    LogoImage.Left := WizardForm.ClientWidth - 200;
    LogoImage.Top := 10;
    LogoImage.Width := 178;
    LogoImage.Height := 58;
    LogoImage.Bitmap.LoadFromFile(LogoFilePath);
  end;
  
  // Add a welcome message
  WizardForm.WelcomeLabel2.Caption := 'This will install {#MyAppName} version {#MyAppVersion} on your computer.' + #13#10 + #13#10 +
                                      'It is recommended that you close all other applications before continuing.' + #13#10 + #13#10 +
                                      'Click Next to continue or Cancel to exit Setup.';
end;

// Clean up on uninstall
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  RegKey: string;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Clean up registry entries
    RegKey := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1';
    if RegKeyExists(HKLM, RegKey) then
      RegDeleteKeyIncludingSubkeys(HKLM, RegKey);
      
    // Also check and remove user-specific registry entries
    RegKey := 'SOFTWARE\{#MyAppPublisher}\{#MyAppName}';
    if RegKeyExists(HKLM, RegKey) then
      RegDeleteKeyIncludingSubkeys(HKLM, RegKey);
    if RegKeyExists(HKCU, RegKey) then
      RegDeleteKeyIncludingSubkeys(HKCU, RegKey);
      
    // Remove startup entry if it exists
    RegKey := 'SOFTWARE\Microsoft\Windows\CurrentVersion\Run';
    if RegValueExists(HKCU, RegKey, '{#MyAppName}') then
      RegDeleteValue(HKCU, RegKey, '{#MyAppName}');
      
    // Clean up user app data if user confirms
    if MsgBox('Do you want to remove all user settings and data associated with {#MyAppName}?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      DelTree(ExpandConstant('{userappdata}\{#MyAppName}'), True, True, True);
      DelTree(ExpandConstant('{localappdata}\{#MyAppName}'), True, True, True);
    end;
    
    // Log completion of uninstall
    Log('Uninstallation completed and cleanup performed');
  end;
end;
function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  AppRunning: Boolean;
  AppExePath: string;
begin
  Result := '';
  
  // Only check for running app if this is an update (not a new installation)
  if RegKeyExists(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1') then
  begin
    // Get the installation path from registry for existing installation
    AppExePath := '';
    if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1', 
                          'InstallLocation', AppExePath) then
    begin
      // Append executable name to the path
      AppExePath := AddBackslash(AppExePath) + '{#MyAppExeName}';
      
      // Double-check if app is still running before installation starts
      AppRunning := CheckAppRunning(AppExePath);
      
      if AppRunning then
      begin
        Result := '{#MyAppName} is still running. Please close it before continuing with the installation.';
      end;
    end;
  end;
end;