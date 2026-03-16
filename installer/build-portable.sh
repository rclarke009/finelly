#!/usr/bin/env bash
# Build Finelly-Portable.zip using only Docker. No Inno Setup required.
# Run from repo root: finelly/installer/build-portable.sh
# Output: finelly/installer/output/Finelly-Portable.zip

set -e
REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FINELY_DIR="$REPO_ROOT/finelly"
OUT_DIR="$REPO_ROOT/finelly/installer/output"
ZIP_NAME="Finelly-Portable.zip"
mkdir -p "$OUT_DIR"

# Use Docker (alpine) to build zip: copy finelly into a clean Finelly folder, exclude cruft, zip
docker run --rm \
  -v "$FINELY_DIR:/src:ro" \
  -v "$OUT_DIR:/out" \
  -w /work \
  alpine:latest \
  sh -c '
    apk add --no-cache zip >/dev/null &&
    rm -rf /work && mkdir -p /work/Finelly &&
    cd /src &&
    for f in *; do
      case "$f" in
        .env|.git|__pycache__|.venv|installer|.idea|.vscode) ;;
        *) cp -R "$f" /work/Finelly/ 2>/dev/null || true ;;
      esac
    done &&
    for dot in .dockerignore .env.example; do [ -f /src/$dot ] && cp /src/$dot /work/Finelly/; done &&
    find /work/Finelly -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true &&
    rm -f /work/Finelly/*.sqlite /work/Finelly/payload.json 2>/dev/null || true &&
    (cd /work && zip -r /out/'"$ZIP_NAME"' Finelly -x "*.DS_Store" "Finelly/installer/*" "*__pycache__*" "*.sqlite" "Finelly/payload.json")
  '

echo "Built: $OUT_DIR/$ZIP_NAME"
echo "Give that ZIP to your dad. He unzips it, runs Setup.bat once, then uses the desktop shortcut (Docker must be installed)."
