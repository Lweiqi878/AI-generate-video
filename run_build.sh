#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/2] Validating 100-work slate..."
python3 scripts/validate_catalog.py

echo "[2/2] Compiling prompts, manifests and offline site..."
python3 scripts/build_all.py

echo
printf 'Build complete.\nOpen: %s\nCatalog: %s\n' \
  "$PWD/generated/site/index.html" \
  "$PWD/generated/catalog/ALL_100.md"
