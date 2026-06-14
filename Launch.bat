@echo off
setlocal EnableDelayedExpansion

title Viscord Launcher
color 0A

echo ===================================================
echo               VISCORD LAUNCH ENGINE
echo ===================================================
echo.

:: Check Python
python --version >nul 2>&1
if %errorlevel% NEQ 0 (
    echo Python not found. Please install Python 3.11 from python.org.
    pause
    exit /b
)

:: Check for updates
if not exist version.txt echo 0.0.0>version.txt
curl -L -s -o remote_version.txt https://raw.githubusercontent.com/Along-the-skies/VISCORD/main/version.txt
if exist remote_version.txt (
    set /p LOCAL=<version.txt
    set /p REMOTE=<remote_version.txt
    if "!LOCAL!" NEQ "!REMOTE!" (
        echo [UPDATE] New version found. Updating...
        curl -L -s -o viscord_update.zip https://github.com/Along-the-skies/VISCORD/archive/refs/heads/main.zip
        powershell -Command "Expand-Archive -Path 'viscord_update.zip' -DestinationPath 'update_temp' -Force"
        robocopy "update_temp\VISCORD-main" "." /E /XF *.bat >nul
        copy /Y remote_version.txt version.txt >nul
        rmdir /S /Q update_temp
        del viscord_update.zip
        echo [SUCCESS] Updated to !REMOTE!.
    )
    del remote_version.txt
)

:: Smart Dependency Check
echo [STATUS] Checking dependencies...
set "DEPS=paho-mqtt supabase numpy sounddevice scipy"
for %%P in (%DEPS%) do (
    python -c "import %%P" >nul 2>&1
    if !errorlevel! NEQ 0 (
        echo [SETUP] Installing %%P...
        python -m pip install %%P >nul 2>&1
    )
)

:: Launch
if not exist Viscord.py (
    echo [ERROR] Viscord.py not found.
    pause
    exit /b
)

echo [STATUS] Launching Viscord...
python Viscord.py
pause