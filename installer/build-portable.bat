@echo off
REM Build Verbiage-Portable.zip using only Docker. No Inno Setup required.
REM Run from project root or from installer. Output: installer\output\Verbiage-Portable.zip

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "VERBIAGE_DIR=%SCRIPT_DIR%.."
set "OUT_DIR=%SCRIPT_DIR%output"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

docker run --rm ^
  -v "%VERBIAGE_DIR%:/src:ro" ^
  -v "%OUT_DIR%:/out" ^
  -w /work ^
  alpine:latest ^
  sh -c "apk add --no-cache zip >/dev/null && rm -rf /work && mkdir -p /work/Verbiage && cd /src && for f in *; do case \"$f\" in .env|.git|__pycache__|.venv|installer|.idea|.vscode) ;; *) cp -R \"$f\" /work/Verbiage/ 2>/dev/null ;; esac; done && for dot in .dockerignore .env.example; do [ -f /src/$dot ] && cp /src/$dot /work/Verbiage/; done && find /work/Verbiage -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; rm -f /work/Verbiage/*.sqlite /work/Verbiage/payload.json 2>/dev/null; (cd /work && zip -r /out/Verbiage-Portable.zip Verbiage -x \"*.DS_Store\" \"Verbiage/installer/*\" \"*__pycache__*\" \"*.sqlite\" \"Verbiage/payload.json\")"

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Built: %OUT_DIR%\Verbiage-Portable.zip
echo Give that ZIP to your dad. He unzips it, runs Setup.bat once, then uses the desktop shortcut.
pause
