#!/usr/bin/env bash
set -e
LEDGERLY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$LEDGERLY_DIR"

# Start Ollama in background if not already responding
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags 2>/dev/null | grep -q 200; then
  echo "Starting Ollama..."
  ollama serve &
  sleep 2
fi

# Wait for Ollama to be ready (up to 30s), then ensure vision model is available for /ask/image and /ingest/image
echo "Waiting for Ollama..."
for i in $(seq 1 30); do
  if curl -s -o /dev/null -w "%{http_code}" http://localhost:11434/api/tags 2>/dev/null | grep -q 200; then
    break
  fi
  if [ "$i" -eq 30 ]; then
    echo "Ollama did not become ready in time. Start it manually (ollama serve) and run this script again."
    exit 1
  fi
  sleep 1
done
echo "Ensuring text LLM (qwen3:8b) is available..."
ollama pull qwen3:8b
echo "Ensuring vision model (llava:7b) is available for image features..."
ollama pull llava:7b

# Prefer .venv, fallback to .venv-mlx
if [ -d ".venv" ]; then
  source .venv/bin/activate
elif [ -d ".venv-mlx" ]; then
  source .venv-mlx/bin/activate
else
  echo "No .venv or .venv-mlx found. Create one and install deps first."
  exit 1
fi

echo "Starting Ledgerly at http://localhost:8000"
# Exclude venv trees — pip installs there trigger endless reload loops with --reload.
exec uvicorn app.main:app --reload \
  --reload-exclude '.venv' \
  --reload-exclude '.venv-mlx'
