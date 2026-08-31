#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/5] Validating 194-work slate..."
python3 scripts/validate_catalog.py

echo "[2/5] Auditing exact and semantic duplicates..."
python3 scripts/audit_duplicates.py --check

echo "[3/5] Compiling prompts, manifests and offline site..."
python3 scripts/build_all.py

echo "[4/5] Building posting cards and upload queue..."
python3 scripts/build_publishing.py

echo "[5/5] Validating publish-ready releases..."
python3 scripts/validate_releases.py

echo
printf 'Build complete.\nOpen: %s\nCatalog: %s\n' \
  "$PWD/generated/site/index.html" \
  "$PWD/generated/catalog/ALL_194.md"
printf 'Publishing: %s\n' "$PWD/publishing/README.md"
