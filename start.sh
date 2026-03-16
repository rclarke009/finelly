#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"

echo "Starting Finelly (Ollama + app)..."
docker compose up -d

echo "Waiting for Ollama to be ready..."
until docker compose exec -T ollama ollama list >/dev/null 2>&1; do
  sleep 2
done

echo "Making sure models are available (one-time download if needed)..."
docker compose exec -T ollama ollama pull qwen3.5:2b
docker compose exec -T ollama ollama pull nomic-embed-text
docker compose exec -T ollama ollama pull qwen2.5vl:7b

echo ""
echo "Ready. Open in your browser: http://localhost:8000/"
echo "To stop later: docker compose down"
