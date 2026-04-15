@echo off
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"

REM Find Python
set "PYTHON="
for %%P in (python.exe python3.exe) do (
    if not defined PYTHON (
        where %%P >nul 2>&1 && set "PYTHON=%%P"
    )
)
if not defined PYTHON (
    echo Python not found. Please run INSTALL_AUTOSTART.bat first.
    pause & exit /b 1
)

REM Find pythonw or fall back to running hidden via VBS
for /f "delims=" %%P in ('where %PYTHON%') do set "PYTHON_FULL=%%P"
for %%D in ("%PYTHON_FULL%") do set "PYTHON_DIR=%%~dpD"
set "PYTHON_DIR=%PYTHON_DIR:~0,-1%"

REM Check if server is already running
curl -s --max-time 1 http://localhost:5000 >nul 2>&1
if %errorlevel%==0 (
    start "" "http://localhost:5000"
    exit /b 0
)

REM Start server silently
if exist "%PYTHON_DIR%\pythonw.exe" (
    start "" /B "%PYTHON_DIR%\pythonw.exe" "%APP_DIR%\server_watcher.pyw"
) else if exist "%APP_DIR%\run_hidden.vbs" (
    start "" /B wscript.exe "%APP_DIR%\run_hidden.vbs"
) else (
    start "" /B "%PYTHON%" "%APP_DIR%\server_watcher.pyw"
)
timeout /t 5 /nobreak >nul
start "" "http://localhost:5000"
