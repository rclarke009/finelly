#!/usr/bin/env bash
# Build Verbiage-Portable.zip using only Docker. No Inno Setup required.
# Run from project root: installer/build-portable.sh
# Output: installer/output/Verbiage-Portable.zip

set -e
VERBIAGE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$VERBIAGE_DIR/installer/output"
ZIP_NAME="Verbiage-Portable.zip"
mkdir -p "$OUT_DIR"

# Use Docker (alpine) to build zip: copy app into a clean Verbiage folder, exclude cruft, zip
docker run --rm \
  -v "$VERBIAGE_DIR:/src:ro" \
  -v "$OUT_DIR:/out" \
  -w /work \
  alpine:latest \
  sh -c '
    apk add --no-cache zip >/dev/null &&
    rm -rf /work && mkdir -p /work/Verbiage &&
    cd /src &&
    for f in *; do
      case "$f" in
        .env|.git|__pycache__|.venv|installer|.idea|.vscode) ;;
        *) cp -R "$f" /work/Verbiage/ 2>/dev/null || true ;;
      esac
    done &&
    for dot in .dockerignore .env.example; do [ -f /src/$dot ] && cp /src/$dot /work/Verbiage/; done &&
    find /work/Verbiage -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true &&
    rm -f /work/Verbiage/*.sqlite /work/Verbiage/payload.json 2>/dev/null || true &&
    (cd /work && zip -r /out/'"$ZIP_NAME"' Verbiage -x "*.DS_Store" "Verbiage/installer/*" "*__pycache__*" "*.sqlite" "Verbiage/payload.json")
  '

echo "Built: $OUT_DIR/$ZIP_NAME"
echo "Give that ZIP to your dad. He unzips it, runs Setup.bat once, then uses the desktop shortcut (Docker must be installed)."
