@echo off
echo Creating desktop shortcut...
set SCRIPT_DIR=%~dp0
set SHORTCUT=%USERPROFILE%\Desktop\Fee Management System.lnk
powershell -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('%SHORTCUT%'); $s.TargetPath = '%SCRIPT_DIR%START.bat'; $s.IconLocation = 'shell32.dll,23'; $s.Description = 'School Fee Management System'; $s.WorkingDirectory = '%SCRIPT_DIR%'; $s.Save()"
echo.
echo Done! Look for "Fee Management System" on your Desktop.
echo Double-click it any time to start the app.
pause
