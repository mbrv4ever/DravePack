@echo off
REM ============================================================
REM  DravePack - starter (zelfherstellend)
REM ============================================================
setlocal
cd /d "%~dp0"

set "PYEXE="
for %%V in (3.13 3.12 3.11 3.10) do (
    if not defined PYEXE (
        py -%%V -c "import sys" >nul 2>&1 && set "PYEXE=py -%%V"
    )
)
if not defined PYEXE (
    python -c "import sys" >nul 2>&1 && set "PYEXE=python"
)
if not defined PYEXE (
    echo Geen geschikte Python gevonden ^(3.10 t/m 3.13^).
    echo Installeer Python van https://www.python.org en probeer opnieuw.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Eenmalig installeren...
    %PYEXE% -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip --quiet
    python -m pip install --only-binary=:all: -r requirements.txt
    REM 7z is optioneel: lukt dit niet, dan werkt de app gewoon zonder 7z.
    python -m pip install --only-binary=:all: py7zr
) else (
    call ".venv\Scripts\activate.bat"
)

REM Zelfherstel: ontbreekt een kernpakket, installeer opnieuw.
python -c "import PyQt6, pyzipper, pycdlib, rarfile" >nul 2>&1
if errorlevel 1 (
    echo Pakketten herstellen...
    python -m pip install --only-binary=:all: -r requirements.txt
    python -m pip install --only-binary=:all: py7zr
)

start "" pythonw app.py
exit /b 0
