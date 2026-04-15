@echo off
setlocal EnableDelayedExpansion

REM ── Auto-elevate: relaunch as admin if not already ─────────────────
REM Guard: if we were already relaunched with --elevated, skip the check
if /i "%~1"=="--elevated" goto :already_admin

REM Reliable admin check via PowerShell (net session is unreliable on many systems)
powershell -NoProfile -Command "([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)" 2>nul | findstr /i "True" >nul
if %errorlevel% equ 0 goto :already_admin

REM Not admin — relaunch elevated, passing --elevated flag to prevent looping
powershell -WindowStyle Hidden -Command "Start-Process cmd.exe -ArgumentList '/c \"\"%~f0\"\" --elevated' -Verb RunAs -Wait"
exit /b

:already_admin

title RPS Fee Management - Installer
cls
echo.
echo  ============================================
echo   RPS Fee Management - Installer v5
echo  ============================================
echo.

set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
set "DESKTOP=%USERPROFILE%\Desktop"

REM ── Find Python ───────────────────────────────────────────────────
set "PYTHON="
for %%P in (python.exe python3.exe) do (
    if not defined PYTHON (
        where %%P >nul 2>&1 && set "PYTHON=%%P"
    )
)
if not defined PYTHON (
    echo  ERROR: Python not found.
    echo  Please install Python from python.org
    echo  Make sure to tick "Add Python to PATH"
    echo.
    echo  Press any key to exit...
    pause >nul
    exit /b 1
)

REM Get full Python directory path
for /f "usebackq delims=" %%P in (`where "%PYTHON%"`) do (
    if not defined PYTHON_FULL set "PYTHON_FULL=%%P"
)
for %%D in ("%PYTHON_FULL%") do set "PYTHON_DIR=%%~dpD"
if "%PYTHON_DIR:~-1%"=="\" set "PYTHON_DIR=%PYTHON_DIR:~0,-1%"
echo  Python: %PYTHON_FULL%

REM ── Find pythonw.exe ──────────────────────────────────────────────
set "PYTHONW="
if exist "%PYTHON_DIR%\pythonw.exe" set "PYTHONW=%PYTHON_DIR%\pythonw.exe"

REM If no pythonw, create a VBS launcher that hides the window
if not defined PYTHONW (
    echo  pythonw not found - creating silent launcher...
    (
        echo Set ws = CreateObject^("WScript.Shell"^)
        echo ws.Run Chr^(34^) ^& "%PYTHON_FULL%" ^& Chr^(34^) ^& " " ^& Chr^(34^) ^& "%APP_DIR%\server_watcher.pyw" ^& Chr^(34^), 0, False
    ) > "%APP_DIR%\run_hidden.vbs"
)

REM ── [1/5] Install packages ────────────────────────────────────────
echo.
echo [1/5] Installing required packages...
"%PYTHON_FULL%" -m pip install flask==3.0.0 werkzeug==3.0.0 reportlab==4.1.0 openpyxl==3.1.2 --quiet --no-warn-script-location >nul 2>&1
echo       Done.

REM ── [2/5] Receipts folder ────────────────────────────────────────
echo [2/5] Creating Receipts folder on Desktop...
set "AY="
for /f "usebackq" %%Y in (`"%PYTHON_FULL%" -c "from datetime import datetime;y=datetime.now().year;m=datetime.now().month;print(str(y)+'-'+str(y+1)[2:] if m>=3 else str(y-1)+'-'+str(y)[2:])"`) do set "AY=%%Y"
if not defined AY set "AY=2026-27"
set "RECEIPTS_DIR=%DESKTOP%\Receipts_%AY%"
if not exist "%RECEIPTS_DIR%\TUITION"   mkdir "%RECEIPTS_DIR%\TUITION"
if not exist "%RECEIPTS_DIR%\MISC"      mkdir "%RECEIPTS_DIR%\MISC"
if not exist "%RECEIPTS_DIR%\CANCELLED" mkdir "%RECEIPTS_DIR%\CANCELLED"
echo       Created: %RECEIPTS_DIR%

REM ── [3/5] Autostart via Task Scheduler ───────────────────────────
echo [3/5] Installing autostart...
schtasks /delete /tn "RPSFeeApp" /f >nul 2>&1

if defined PYTHONW (
    set "TASK_CMD=\"%PYTHONW%\" \"%APP_DIR%\server_watcher.pyw\""
) else (
    set "TASK_CMD=wscript.exe \"%APP_DIR%\run_hidden.vbs\""
)

schtasks /create /tn "RPSFeeApp" /tr "!TASK_CMD!" /sc ONLOGON /rl HIGHEST /f >nul 2>&1
if !errorlevel!==0 (
    echo       Task Scheduler: OK
) else (
    echo       Task Scheduler failed - using Startup folder instead...
    set "STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
    if defined PYTHONW (
        echo Set ws = CreateObject^("WScript.Shell"^) > "!STARTUP!\RPS_FeeApp.vbs"
        echo ws.Run Chr^(34^) ^& "%PYTHONW%" ^& Chr^(34^) ^& " " ^& Chr^(34^) ^& "%APP_DIR%\server_watcher.pyw" ^& Chr^(34^), 0, False >> "!STARTUP!\RPS_FeeApp.vbs"
    ) else (
        echo Set ws = CreateObject^("WScript.Shell"^) > "!STARTUP!\RPS_FeeApp.vbs"
        echo ws.Run Chr^(34^) ^& "%PYTHON_FULL%" ^& Chr^(34^) ^& " " ^& Chr^(34^) ^& "%APP_DIR%\server_watcher.pyw" ^& Chr^(34^), 0, False >> "!STARTUP!\RPS_FeeApp.vbs"
    )
    echo       Startup folder: OK
)

REM ── [4/5] Desktop shortcuts ───────────────────────────────────────
echo [4/5] Creating desktop shortcuts...

REM App shortcut
set "VBS1=%TEMP%\sc_app.vbs"
(
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo Set s = ws.CreateShortcut^("%DESKTOP%\RPS Fee App.lnk"^)
    echo s.TargetPath = "%APP_DIR%\OpenApp.bat"
    echo s.WorkingDirectory = "%APP_DIR%"
    echo s.WindowStyle = 7
    echo s.Description = "Open RPS Fee Management App"
    echo s.Save
) > "%VBS1%"
cscript //nologo "%VBS1%" >nul 2>&1
del "%VBS1%" >nul 2>&1

REM Receipts shortcut
set "VBS2=%TEMP%\sc_rec.vbs"
(
    echo Set ws = CreateObject^("WScript.Shell"^)
    echo Set s = ws.CreateShortcut^("%DESKTOP%\Receipts_%AY%.lnk"^)
    echo s.TargetPath = "%RECEIPTS_DIR%"
    echo s.Description = "RPS Receipts %AY%"
    echo s.Save
) > "%VBS2%"
cscript //nologo "%VBS2%" >nul 2>&1
del "%VBS2%" >nul 2>&1
echo       Done.

REM ── [5/5] Start server ────────────────────────────────────────────
echo [5/5] Starting server...
if defined PYTHONW (
    start "" /B "%PYTHONW%" "%APP_DIR%\server_watcher.pyw"
) else (
    start "" /B wscript.exe "%APP_DIR%\run_hidden.vbs"
)
timeout /t 5 /nobreak >nul
start "" "http://localhost:5000"

echo.
echo  ============================================
echo   DONE! App is running.
echo   Open browser: http://localhost:5000
echo   Desktop shortcuts:
echo     "RPS Fee App" - opens the app
echo     "Receipts_%AY%" - opens PDF folder
echo  ============================================
echo.
echo  This window will close in 10 seconds...
timeout /t 10 /nobreak >nul
