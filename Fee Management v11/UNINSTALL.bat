@echo off
setlocal EnableDelayedExpansion

REM ── Auto-elevate to Administrator ─────────────────────────────────
net session >nul 2>&1
if %errorlevel% neq 0 (
    powershell -WindowStyle Hidden -Command "Start-Process cmd.exe -ArgumentList '/c \"%~f0\"' -Verb RunAs -Wait"
    exit /b
)

title RPS Fee Management - Uninstaller
cls
echo.
echo  ============================================
echo   RPS Fee Management - Uninstaller
echo  ============================================
echo.
echo  This will:
echo    1. Stop the running server
echo    2. Remove autostart (Task Scheduler + Startup folder)
echo    3. Remove Desktop shortcuts
echo    4. Leave your Receipts folder UNTOUCHED
echo.
echo  Press any key to continue, or close this window to cancel...
pause >nul

echo.
echo [1/3] Stopping server...

REM Kill pythonw.exe processes
taskkill /F /IM pythonw.exe >nul 2>&1
REM Kill python.exe running server_watcher or app.py
for /f "tokens=1" %%P in ('wmic process where "name='python.exe' and commandline like '%%server_watcher%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%P >nul 2>&1
)
for /f "tokens=1" %%P in ('wmic process where "name='python.exe' and commandline like '%%app.py%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%P >nul 2>&1
)
REM Kill wscript running run_hidden.vbs
for /f "tokens=1" %%P in ('wmic process where "name='wscript.exe' and commandline like '%%run_hidden%%'" get processid 2^>nul ^| findstr /r "[0-9]"') do (
    taskkill /F /PID %%P >nul 2>&1
)
echo       Server stopped.

echo [2/3] Removing autostart...
REM Remove Task Scheduler task
schtasks /delete /tn "RPSFeeApp" /f >nul 2>&1
echo       Task Scheduler entry removed.

REM Remove Startup folder VBS
set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
if exist "%STARTUP%\RPS_FeeApp.vbs" (
    del /f "%STARTUP%\RPS_FeeApp.vbs" >nul 2>&1
    echo       Startup folder entry removed.
)

echo [3/3] Removing Desktop shortcuts...
set "DESKTOP=%USERPROFILE%\Desktop"
if exist "%DESKTOP%\RPS Fee App.lnk"       del /f "%DESKTOP%\RPS Fee App.lnk" >nul 2>&1
REM Remove any Receipts_YYYY-YY shortcut
for %%F in ("%DESKTOP%\Receipts_*.lnk") do del /f "%%F" >nul 2>&1
echo       Shortcuts removed.

echo.
echo  ============================================
echo   DONE. Server is stopped and autostart removed.
echo.
echo   You can now safely DELETE these folders:
echo     %~dp0  (this app folder)
echo     %USERPROFILE%\Desktop\Receipts_*  (if you want)
echo.
echo   NOTE: Receipts folder has NOT been deleted.
echo   Delete it manually only if you are sure.
echo  ============================================
echo.
echo  This window will close in 15 seconds...
timeout /t 15 /nobreak >nul
