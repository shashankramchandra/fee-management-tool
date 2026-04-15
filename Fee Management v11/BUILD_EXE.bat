@echo off
setlocal enabledelayedexpansion
title Build School Fee EXE
color 0B
cls
echo.
echo  ==================================================
echo    BUILD STANDALONE EXE (no Python needed)
echo  ==================================================
echo.

python --version >nul 2>&1
if !errorlevel! neq 0 (
    echo  ERROR: Python not found. Install Python first.
    pause & exit /b 1
)

echo  Installing build tools...
pip install pyinstaller flask reportlab werkzeug openpyxl --quiet --disable-pip-version-check
echo  Done.
echo.

cd /d "%~dp0"

echo  Building EXE (takes 3-5 minutes, please wait)...
echo.

pyinstaller --onefile --noconsole ^
    --name "SchoolFeeSystem" ^
    --add-data "templates;templates" ^
    --add-data "static;static" ^
    --hidden-import "werkzeug.security" ^
    --hidden-import "werkzeug.utils" ^
    --hidden-import "reportlab.pdfgen.canvas" ^
    --hidden-import "reportlab.lib.pagesizes" ^
    --hidden-import "reportlab.lib.styles" ^
    --hidden-import "reportlab.lib.units" ^
    --hidden-import "reportlab.lib.colors" ^
    --hidden-import "reportlab.platypus" ^
    --hidden-import "reportlab.platypus.tables" ^
    --hidden-import "openpyxl" ^
    --hidden-import "openpyxl.styles" ^
    --hidden-import "flask.templating" ^
    --hidden-import "jinja2" ^
    --hidden-import "sqlite3" ^
    app.py

if !errorlevel! neq 0 (
    echo.
    echo  BUILD FAILED. See errors above.
    pause & exit /b 1
)

echo.
echo  ==================================================
echo    BUILD SUCCESSFUL!
echo  ==================================================
echo.
echo    EXE is at: dist\SchoolFeeSystem.exe
echo.
echo    To deploy on another computer:
echo    1. Copy  dist\SchoolFeeSystem.exe
echo    2. Copy  database\  folder (has your data)
echo    3. Copy  receipts\  folder (PDF storage)
echo    4. Put all 3 in the same folder
echo    5. Double-click SchoolFeeSystem.exe
echo.
echo    No Python installation needed on that computer!
echo  ==================================================
echo.
pause
