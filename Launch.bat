@echo off
setlocal EnableDelayedExpansion

title Viscord Launcher
color 0A

echo ===================================================
echo               VISCORD LAUNCH ENGINE
echo ===================================================
echo.

:: =========================
:: Check Python
:: =========================
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found. Downloading Python...
    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

    if not exist python_installer.exe (
        echo [ERROR] Failed to download Python.
        pause
        exit /b
    )

    echo Installing Python silently...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    del python_installer.exe

    echo Python installed successfully. Please run this script again.
    pause
    exit /b
)

:: =========================
:: Check for updates
:: =========================
if not exist version.txt echo 0.0.0>version.txt

curl -L -s -o remote_version.txt https://raw.githubusercontent.com/Along-the-skies/VISCORD/main/version.txt

if exist remote_version.txt (
    set /p LOCAL=<version.txt
    set /p REMOTE=<remote_version.txt

    if not "!LOCAL!"=="!REMOTE!" (
        echo [UPDATE] New update found (!LOCAL! -> !REMOTE!)...
        curl -L -s -o viscord_update.zip https://github.com/Along-the-skies/VISCORD/archive/refs/heads/main.zip

        if exist viscord_update.zip (
            powershell -Command "Expand-Archive -Path 'viscord_update.zip' -DestinationPath 'update_temp' -Force"
            robocopy "update_temp\VISCORD-main" "." /E /XF *.bat >nul
            copy /Y remote_version.txt version.txt >nul
            rmdir /S /Q update_temp
            del viscord_update.zip
            echo [SUCCESS] Application files updated to version !REMOTE!.
        ) else (
            echo [WARNING] Failed to download update zip package. Proceeding...
        )
    ) else (
        echo [STATUS] System up to date (Version: !LOCAL!).
    )
    del remote_version.txt
)

:: =========================
:: Smart Dependency Verification
:: =========================
set "MISSING_DEP=0"
for %%P in (paho.mqtt supabase numpy sounddevice scipy) do (
    python -c "import %%P" >nul 2>&1
    if errorlevel 1 (
        set "MISSING_DEP=1"
        echo [SETUP] Dependency '%%P' missing. Staging module configuration...
    )
)

if "!MISSING_DEP!"=="1" (
    echo [SETUP] Installing required modules. Please wait...
    python -m pip install --upgrade pip >nul 2>&1
    python -m pip install paho-mqtt supabase numpy sounddevice scipy >nul
    if errorlevel 1 (
        echo.
        echo [ERROR] Pipeline execution failed. Dependency stack installation failed.
        pause
        exit /b
    )
    echo [SETUP] All software dependencies configured.
) else (
    echo [STATUS] Environment modules verified.
)

:: =========================
:: Launch Viscord
:: =========================
if not exist Viscord.py (
    echo [ERROR] Viscord.py core process entry point not found.
    pause
    exit /b
)

echo.
echo Launching Viscord core client runtime...
echo.

python Viscord.py

echo.
echo Viscord interface closed.
pause