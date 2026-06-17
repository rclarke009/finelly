@echo off
cd /d "%~dp0"

echo Starting Ledgerly (Postgres+pgvector internal, Ollama, app, finance MCP)...
docker compose up -d
echo Finance tools MCP (optional, for Cursor): http://localhost:8001/mcp — set FINNHUB_API_KEY in .env for live quotes.

echo Waiting for Ollama to be ready...
:wait
docker compose exec ollama ollama list >nul 2>&1
if errorlevel 1 (
  timeout /t 3 /nobreak >nul
  goto wait
)

echo Checking models (skip if already installed)...
docker compose exec ollama ollama list 2>nul | findstr /C:"qwen3:8b" >nul 2>&1
if errorlevel 1 (
  echo Pulling qwen3:8b...
  docker compose exec ollama ollama pull qwen3:8b
) else echo qwen3:8b already present.
docker compose exec ollama ollama list 2>nul | findstr /C:"nomic-embed-text" >nul 2>&1
if errorlevel 1 (
  echo Pulling nomic-embed-text...
  docker compose exec ollama ollama pull nomic-embed-text
) else echo nomic-embed-text already present.
docker compose exec ollama ollama list 2>nul | findstr /C:"llava:7b" >nul 2>&1
if errorlevel 1 (
  echo Pulling llava:7b...
  docker compose exec ollama ollama pull llava:7b
) else echo llava:7b already present.

echo Waiting for Ledgerly web app...
:waitapp
curl -sf http://localhost:8000/health 2>nul | findstr /C:"\"healthy\":true" >nul 2>&1
if errorlevel 1 (
  timeout /t 2 /nobreak >nul
  goto waitapp
)

echo.
echo Ready. Opening browser...
start http://localhost:8000/
echo To stop later: docker compose down
pause
