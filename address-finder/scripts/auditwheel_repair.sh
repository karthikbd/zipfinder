#!/usr/bin/env bash
# Step 5: Build + repair wheel so it's self-contained (manylinux).
# Requires: pip install auditwheel  (Linux)
#           pip install delocate    (macOS)
set -euo pipefail

echo "==> Building wheel …"
pip wheel . -w dist/ --no-deps

echo "==> Repairing wheel (bundles all .so dependencies) …"
if command -v auditwheel &>/dev/null; then
    auditwheel repair dist/address_finder-*.whl --wheel-dir dist/repaired/
elif command -v delocate-wheel &>/dev/null; then
    delocate-wheel dist/address_finder-*.whl -w dist/repaired/
else
    echo "No auditwheel/delocate found. Wheel may not be portable."
fi

echo "==> Final wheels:"
ls -lh dist/repaired/ 2>/dev/null || ls -lh dist/
