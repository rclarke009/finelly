@echo off
REM Build Finelly-Portable.zip using only Docker. No Inno Setup required.
REM Run from repo root or from finelly/installer. Output: finelly\installer\output\Finelly-Portable.zip

cd /d "%~dp0"
set "SCRIPT_DIR=%~dp0"
set "FINELY_DIR=%SCRIPT_DIR%.."
set "REPO_ROOT=%SCRIPT_DIR%..\.."
set "OUT_DIR=%SCRIPT_DIR%output"
if not exist "%OUT_DIR%" mkdir "%OUT_DIR%"

docker run --rm ^
  -v "%FINELY_DIR%:/src:ro" ^
  -v "%OUT_DIR%:/out" ^
  -w /work ^
  alpine:latest ^
  sh -c "apk add --no-cache zip >/dev/null && rm -rf /work && mkdir -p /work/Finelly && cd /src && for f in *; do case \"$f\" in .env|.git|__pycache__|.venv|installer|.idea|.vscode) ;; *) cp -R \"$f\" /work/Finelly/ 2>/dev/null ;; esac; done && for dot in .dockerignore .env.example; do [ -f /src/$dot ] && cp /src/$dot /work/Finelly/; done && find /work/Finelly -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null; rm -f /work/Finelly/*.sqlite /work/Finelly/payload.json 2>/dev/null; (cd /work && zip -r /out/Finelly-Portable.zip Finelly -x \"*.DS_Store\" \"Finelly/installer/*\" \"*__pycache__*\" \"*.sqlite\" \"Finelly/payload.json\")"

if errorlevel 1 (
  echo Build failed.
  pause
  exit /b 1
)
echo.
echo Built: %OUT_DIR%\Finelly-Portable.zip
echo Give that ZIP to your dad. He unzips it, runs Setup.bat once, then uses the desktop shortcut.
pause
