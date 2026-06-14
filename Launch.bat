@echo off
setlocal EnableDelayedExpansion

title Viscord Setup and Launcher
color 0A

echo ===================================================
echo               VISCORD SETUP
echo ===================================================
echo.

:: =========================
:: Check Python
:: =========================
python --version >nul 2>&1
if errorlevel 1 (
    echo Python not found.
    echo Downloading Python...

    curl -L -o python_installer.exe https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe

    if not exist python_installer.exe (
        echo Failed to download Python.
        pause
        exit /b
    )

    echo Installing Python...
    start /wait python_installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0

    del python_installer.exe

    echo.
    echo Python installed.
    echo Please run this file again.
    pause
    exit /b
)

echo Python detected.
echo.

:: =========================
:: Create local version file
:: =========================
if not exist version.txt (
    echo 0.0.0>version.txt
)

:: =========================
:: Check for updates
:: =========================
echo Checking for updates...

curl -L -o remote_version.txt ^
https://raw.githubusercontent.com/Along-the-skies/VISCORD/main/version.txt

if exist remote_version.txt (

    set /p LOCAL=<version.txt
    set /p REMOTE=<remote_version.txt

    echo Local Version : !LOCAL!
    echo Remote Version: !REMOTE!

    if not "!LOCAL!"=="!REMOTE!" (

        echo.
        echo Update found!
        echo Downloading latest version...
        echo.

        curl -L -o viscord_update.zip ^
        https://github.com/Along-the-skies/VISCORD/archive/refs/heads/main.zip

        if exist viscord_update.zip (

            powershell -Command ^
            "Expand-Archive -Path 'viscord_update.zip' -DestinationPath 'update_temp' -Force"

            robocopy "update_temp\VISCORD-main" "." /E /XF *.bat >nul

            copy /Y remote_version.txt version.txt >nul

            rmdir /S /Q update_temp
            del viscord_update.zip

            echo Update completed.
        ) else (
            echo Failed to download update.
        )

    ) else (
        echo Already up to date.
    )

    del remote_version.txt
)

echo.
echo Upgrading pip...
python -m pip install --upgrade pip

echo.
echo Installing Viscord dependencies...

python -m pip install ^
paho-mqtt ^
supabase ^
numpy ^
sounddevice ^
scipy

if errorlevel 1 (
    echo.
    echo Some packages failed to install.
    pause
    exit /b
)

:: =========================
:: Launch Viscord
:: =========================
if not exist Viscord.py (
    echo.
    echo ERROR: Viscord.py not found.
    pause
    exit /b
)

echo.
echo Launching Viscord...
echo.

python Viscord.py

echo.
echo Viscord closed.
pause