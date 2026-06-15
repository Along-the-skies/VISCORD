:: Copyright 2026 Vasudev
::
:: Licensed under the Apache License, Version 2.0 (the "License");
:: you may not use this file except in compliance with the License.
:: You may obtain a copy of the License at
::
::     http://www.apache.org/licenses/LICENSE-2.0
::
:: Unless required by applicable law or agreed to in writing, software
:: distributed under the License is distributed on an "AS IS" BASIS,
:: WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
:: See the License for the specific language governing permissions and
:: limitations under the License.

@echo off
setlocal EnableDelayedExpansion

:: Change to script directory
cd /d "%~dp0"

:: Define ANSI color codes
set "ESC="
for /F %%A in ('copy /Z "%~f0" nul') do set "ESC=%%A"

set "COLOR_WHITE=!ESC![97m"
set "COLOR_YELLOW=!ESC![93m"
set "COLOR_DEFAULT=!ESC![0m"

title Viscord Launcher

cls
echo.
echo ===================================================
echo               VISCORD LAUNCH ENGINE
echo ===================================================
echo.

:: ============================================================
:: Helper Functions for Output
:: ============================================================

goto :main

:status
    echo !COLOR_YELLOW![STATUS]!COLOR_DEFAULT! %~1
    exit /b

:success
    echo !COLOR_YELLOW![SUCCESS]!COLOR_DEFAULT! %~1
    exit /b

:warning
    echo !COLOR_YELLOW![WARNING]!COLOR_DEFAULT! %~1
    exit /b

:error
    echo !COLOR_YELLOW![ERROR]!COLOR_DEFAULT! %~1
    exit /b

:: ============================================================
:: Main Script
:: ============================================================

:main

:: Check Python availability
python --version >nul 2>&1
if !errorlevel! NEQ 0 (
    call :error "Python not found. Please install Python 3.11 from python.org"
    pause
    exit /b 1
)

:: Check pip availability
python -m pip --version >nul 2>&1
if !errorlevel! NEQ 0 (
    call :status "pip not found. Upgrading Python installation..."
    python -m ensurepip --upgrade >nul 2>&1
    if !errorlevel! NEQ 0 (
        call :error "Failed to install pip. Please repair Python installation."
        pause
        exit /b 1
    )
)

:: Check installation status (both files required)
set "INSTALLED=1"
if not exist version.txt set "INSTALLED=0"
if not exist Viscord.py set "INSTALLED=0"

if !INSTALLED! EQU 0 (
    call :status "Installation files missing. Downloading from GitHub..."
    call :download_and_install
    if !errorlevel! NEQ 0 exit /b 1
) else (
    :: Check for launcher updates (independent of version)
    call :check_launcher_update
    
    :: Check for application updates
    call :check_application_update
)

:: Check and install dependencies
call :check_dependencies

:: Print installed version before launch
if exist version.txt (
    for /f "usebackq delims=" %%V in ("version.txt") do set "LOCAL_VERSION=%%V"
) else (
    set "LOCAL_VERSION=unknown"
)
call :status "Current installed version: !LOCAL_VERSION!"

:: Final launch
if not exist Viscord.py (
    call :error "Viscord.py not found."
    pause
    exit /b 1
)

call :status "Launching Viscord..."
python Viscord.py
pause
exit /b 0

:: ============================================================
:: Check Launcher Update
:: ============================================================

:check_launcher_update
    setlocal EnableDelayedExpansion
    
    call :status "Checking launcher updates..."
    
    curl -L -s -o remote_launch.bat https://raw.githubusercontent.com/Along-the-skies/VISCORD/main/Launch.bat >nul 2>&1
    if not exist remote_launch.bat (
        call :warning "Cannot reach GitHub. Skipping launcher check."
        endlocal
        exit /b 0
    )
    
    :: Compare files
    fc /B Launch.bat remote_launch.bat >nul 2>&1
    if !errorlevel! EQU 0 (
        del remote_launch.bat
        endlocal
        exit /b 0
    )
    
    :: Launcher is different, update repository
    call :status "New launcher version found. Updating repository..."
    call :download_and_install
    
    endlocal
    exit /b 0

:: ============================================================
:: Check Application Update
:: ============================================================

:check_application_update
    setlocal EnableDelayedExpansion
    
    call :status "Checking for updates..."
    
    curl -L -s -o remote_version.txt https://raw.githubusercontent.com/Along-the-skies/VISCORD/main/version.txt >nul 2>&1
    if not exist remote_version.txt (
        call :warning "Cannot reach GitHub. Skipping version check."
        endlocal
        exit /b 0
    )
    
    for /f "usebackq delims=" %%A in ("version.txt") do set "LOCAL=%%A"
    for /f "usebackq delims=" %%B in ("remote_version.txt") do set "REMOTE=%%B"
    
    :: Use PowerShell for version comparison
    powershell -Command "$ErrorActionPreference='Stop'; try { $local=[version]'!LOCAL!'; $remote=[version]'!REMOTE!'; if ($remote -gt $local) { exit 1 } else { exit 0 } } catch { exit 2 }" >nul 2>&1
    if !errorlevel! EQU 1 (
        :: Version is older, update
        call :status "New version found (!REMOTE!). Updating..."
        call :download_and_install
        if !errorlevel! EQU 0 (
            call :success "Updated to !REMOTE!."
        )
    ) else if !errorlevel! EQU 0 (
        call :status "No update needed. Local version !LOCAL! is current."
    ) else (
        call :warning "Version comparison failed; skipping update to avoid downgrade."
    )
    
    del remote_version.txt
    endlocal
    exit /b 0

:: ============================================================
:: Download and Install
:: ============================================================

:download_and_install
    setlocal EnableDelayedExpansion
    
    call :status "Downloading from GitHub..."
    
    curl -L -s -o viscord_install.zip https://github.com/Along-the-skies/VISCORD/archive/refs/heads/main.zip >nul 2>&1
    if !errorlevel! NEQ 0 (
        call :error "Failed to download. Please check your internet connection."
        endlocal
        exit /b 1
    )
    
    call :status "Extracting files..."
    
    powershell -Command "Expand-Archive -Path 'viscord_install.zip' -DestinationPath 'install_temp' -Force" >nul 2>&1
    if !errorlevel! NEQ 0 (
        call :error "Failed to extract archive."
        del viscord_install.zip
        endlocal
        exit /b 1
    )
    
    call :status "Installing repository..."
    
    :: Preserve existing version.txt if local version is newer than remote
    set "PRESERVE_VERSION=0"
    if exist version.txt if exist "install_temp\VISCORD-main\version.txt" (
        for /f "usebackq delims=" %%A in ("version.txt") do set "LOCAL=%%A"
        for /f "usebackq delims=" %%B in ("install_temp\VISCORD-main\version.txt") do set "REMOTE=%%B"
        powershell -Command "$ErrorActionPreference='Stop'; try { $local=[version]'!LOCAL!'; $remote=[version]'!REMOTE!'; if ($local -gt $remote) { exit 1 } else { exit 0 } } catch { exit 2 }" >nul 2>&1
        if !errorlevel! EQU 1 (
            set "PRESERVE_VERSION=1"
            call :warning "Local version !LOCAL! is newer than remote !REMOTE!. Preserving version.txt."
        ) else if !errorlevel! EQU 2 (
            set "PRESERVE_VERSION=1"
            call :warning "Version comparison failed during install. Preserving existing version.txt."
        )
    )
    
    if !PRESERVE_VERSION! EQU 1 (
        robocopy "install_temp\VISCORD-main" "." /E /XF Launch.bat version.txt >nul 2>&1
    ) else (
        robocopy "install_temp\VISCORD-main" "." /E /XF Launch.bat >nul 2>&1
    )
    
    :: Cleanup
    rmdir /S /Q install_temp >nul 2>&1
    del viscord_install.zip >nul 2>&1
    if exist remote_launch.bat del remote_launch.bat >nul 2>&1
    
    call :success "Installation complete."
    
    endlocal
    exit /b 0

:: ============================================================
:: Check and Install Dependencies
:: ============================================================

:check_dependencies
    setlocal EnableDelayedExpansion
    
    call :status "Checking dependencies..."
    
    set "DEPS[0]=paho.mqtt.client,paho-mqtt"
    set "DEPS[1]=supabase,supabase"
    set "DEPS[2]=numpy,numpy"
    set "DEPS[3]=sounddevice,sounddevice"
    set "DEPS[4]=scipy,scipy"
    
    for /L %%I in (0,1,4) do (
        for /f "tokens=1,2 delims=," %%A in ("!DEPS[%%I]!") do (
            python -c "import %%A" >nul 2>&1
            if !errorlevel! NEQ 0 (
                call :status "Installing %%B..."
                python -m pip install %%B >nul 2>&1
                if !errorlevel! NEQ 0 (
                    call :warning "Failed to install %%B. Continuing anyway..."
                )
            )
        )
    )
    
    endlocal
    exit /b 0