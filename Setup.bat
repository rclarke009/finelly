@echo off
setlocal
set "INSTALL_DIR=%LocalAppData%\Finelly"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"

echo Installing Finelly to %INSTALL_DIR%...
mkdir "%INSTALL_DIR%" 2>nul

:: Copy files, excluding dev/secrets and installer build artifacts
robocopy "%HERE%" "%INSTALL_DIR%" /E /XD .git __pycache__ .venv installer .idea .vscode /XF .env *.zip /NFL /NDL /NJH /NJS /nc /ns /np
if errorlevel 8 (
  echo Robocopy failed.
  pause
  exit /b 1
)

:: Create desktop shortcut (PowerShell)
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$WshShell = New-Object -ComObject WScript.Shell;" ^
  "$Shortcut = $WshShell.CreateShortcut([Environment]::GetFolderPath('Desktop') + '\\Finelly.lnk');" ^
  "$Shortcut.TargetPath = '%INSTALL_DIR%\Start.bat';" ^
  "$Shortcut.WorkingDirectory = '%INSTALL_DIR%';" ^
  "$Shortcut.Description = 'Start Finelly (Docker)';" ^
  "$Shortcut.Save()"

echo.
echo Installation complete. A "Finelly" shortcut is on your desktop.
echo You can close this window and delete the folder you extracted if you like.
echo.
echo To start: double-click the desktop shortcut (Docker must be running).
pause
