@echo off
title RPS Fee App — Starting...
set "APP_DIR=%~dp0"
if "%APP_DIR:~-1%"=="\" set "APP_DIR=%APP_DIR:~0,-1%"
set "PYTHON=%APP_DIR%\python\python.exe"

REM Ensure receipts folders exist next to app folder
for %%i in ("%APP_DIR%") do set "PARENT_DIR=%%~dpi"
if "%PARENT_DIR:~-1%"=="\" set "PARENT_DIR=%PARENT_DIR:~0,-1%"
set "RECEIPTS_DIR=%PARENT_DIR%\receipts"
if not exist "%RECEIPTS_DIR%\TUITION"   mkdir "%RECEIPTS_DIR%\TUITION"
if not exist "%RECEIPTS_DIR%\MISC"      mkdir "%RECEIPTS_DIR%\MISC"
if not exist "%RECEIPTS_DIR%\CANCELLED" mkdir "%RECEIPTS_DIR%\CANCELLED"

start "" /B "%PYTHON%" "%APP_DIR%\app.py"
timeout /t 3 /nobreak >nul
start "" "http://localhost:5000"
