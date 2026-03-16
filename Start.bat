@echo off
cd /d "%~dp0"

echo Starting Finelly (Ollama + app)...
docker compose up -d

echo Waiting for Ollama to be ready...
:wait
docker compose exec ollama ollama list >nul 2>&1
if errorlevel 1 (
  timeout /t 3 /nobreak >nul
  goto wait
)

echo Checking models (skip if already installed)...
docker compose exec ollama ollama list 2>nul | findstr /C:"qwen3.5:2b" >nul 2>&1
if errorlevel 1 (
  echo Pulling qwen3.5:2b...
  docker compose exec ollama ollama pull qwen3.5:2b
) else echo qwen3.5:2b already present.
docker compose exec ollama ollama list 2>nul | findstr /C:"nomic-embed-text" >nul 2>&1
if errorlevel 1 (
  echo Pulling nomic-embed-text...
  docker compose exec ollama ollama pull nomic-embed-text
) else echo nomic-embed-text already present.
docker compose exec ollama ollama list 2>nul | findstr /C:"qwen2.5vl" >nul 2>&1
if errorlevel 1 (
  echo Pulling qwen2.5vl:7b...
  docker compose exec ollama ollama pull qwen2.5vl:7b
) else echo qwen2.5vl already present.

echo.
echo Ready. Opening browser...
start http://localhost:8000/
echo To stop later: docker compose down
pause
