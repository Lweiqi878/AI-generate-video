#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/3] Validating 194-work slate..."
python3 scripts/validate_catalog.py

echo "[2/3] Auditing exact and semantic duplicates..."
python3 scripts/audit_duplicates.py --check

echo "[3/3] Compiling prompts, manifests and offline site..."
python3 scripts/build_all.py

echo
printf 'Build complete.\nOpen: %s\nCatalog: %s\n' \
  "$PWD/generated/site/index.html" \
  "$PWD/generated/catalog/ALL_194.md"
