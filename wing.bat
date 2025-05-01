@echo off
echo Starting prerequisite installation for VANTA...
echo NOTE: Please run this script as Administrator.
echo.
pause

REM == 1. Check/Install Winget (via PowerShell) ==
echo [Step 1/4] Checking/Installing Winget (App Installer)...
powershell -ExecutionPolicy Bypass -Command "if (!(Get-Command winget -ErrorAction SilentlyContinue)) { Write-Host 'Attempting to download and install Winget...'; try { Invoke-WebRequest -Uri \"https://github.com/microsoft/winget-cli/releases/latest/download/Microsoft.DesktopAppInstaller_8wekyb3d8bbwe.msixbundle\" -OutFile \"$env:TEMP\winget_installer.msixbundle\" -ErrorAction Stop; Write-Host 'Stopping potentially running AppInstaller process...'; Get-Process -Name \"AppInstallerCLI\" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue; Write-Host 'Installing AppInstaller (winget)...'; Add-AppxPackage -Path \"$env:TEMP\winget_installer.msixbundle\" -ErrorAction Stop; Write-Host 'Winget installation successful.'; } catch { Write-Warning \"Winget download/install failed: $($_.Exception.Message)\"; } } else { Write-Host 'Winget appears to be installed.'; }"
echo.

REM == 2. Install VS Build Tools (Base using Winget) ==
echo [Step 2/4] Attempting to install Visual Studio Build Tools using Winget...
winget install Microsoft.VisualStudio.BuildTools --accept-package-agreements --accept-source-agreements --id Microsoft.VisualStudio.BuildTools
IF %ERRORLEVEL% NEQ 0 (
    echo WARNING: Failed to install VS Build Tools using winget. Check winget status or install manually.
) else (
    echo VS Build Tools base package installation command executed.
)
echo IMPORTANT: Manual step needed later - Run Visual Studio Installer, select 'Modify' on Build Tools, ensure 'Desktop development with C++' workload is installed!
echo.

REM == 3. Install Rust ==
echo [Step 3/4] Installing Rust...
echo Checking for rustup-init.exe in Downloads folder (%USERPROFILE%\Downloads)...
IF EXIST "%USERPROFILE%\Downloads\rustup-init.exe" (
    echo Found rustup-init.exe. Running installer...
    echo Please follow the prompts in the Rust installer window (usually select option 1 for default).
    "%USERPROFILE%\Downloads\rustup-init.exe"
) ELSE (
    echo rustup-init.exe not found in Downloads.
    echo Please download it from https://rustup.rs/ and run it manually to install Rust.
    pause
)
echo.

REM == 4. User Instructions for Final Steps ==
echo [Step 4/4] FINAL MANUAL STEPS REQUIRED:
echo ================================================================================
echo PREREQUISITE INSTALLATION ATTEMPT COMPLETE.
echo ================================================================================
echo.
echo PLEASE PERFORM THE FOLLOWING MANUAL STEPS NOW:
echo.
echo 1. VERIFY C++ Tools: 
echo    - Open the 'Visual Studio Installer' application.
echo    - Find 'Visual Studio Build Tools 2022', click 'Modify'.
echo    - Ensure the 'Desktop development with C++' workload is CHECKED and INSTALLED. 
echo      (Install it if it's not). Close the installer when done.
echo.
echo 2. Open 'Developer PowerShell for VS 2022' AS ADMINISTRATOR.
echo    (Search for it in the Start Menu, right-click -> Run as administrator)
echo.
echo 3. In the Developer PowerShell window, navigate to your project:
echo    cd %CD%
echo.
echo 4. Activate your virtual environment:
echo    .\.venv\Scripts\Activate.ps1
echo.
echo 5. Run the final pip install command:
echo    pip install -r requirements.txt
echo.
echo ================================================================================
echo Script finished. Please complete the manual steps above.
echo ================================================================================
echo.
pause
