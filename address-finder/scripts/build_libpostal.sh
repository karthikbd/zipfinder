#!/usr/bin/env bash
# Compile libpostal (parser-data branch) and download model data.
# Outputs:
#   address_finder/_libs/libpostal.so.1  — compiled shared library
#   /tmp/postal_raw/                      — raw model data (pre-quantization)

set -euo pipefail

REPO_URL="https://github.com/openvenues/libpostal"
BRANCH="master"
BUILD_DIR="/tmp/libpostal_build"
DATA_DIR="/tmp/postal_raw"
LIB_OUT="$(pwd)/address_finder/_libs"

echo "==> Cloning libpostal …"
rm -rf "$BUILD_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$BUILD_DIR"
cd "$BUILD_DIR"

echo "==> Bootstrap & configure …"
./bootstrap.sh
# --disable-data-download: don't auto-download at build time
# We control data placement manually
./configure --datadir="$DATA_DIR" --disable-data-download

echo "==> Compiling …"
make -j"$(nproc)"

echo "==> Copying shared library …"
mkdir -p "$LIB_OUT"
cp src/.libs/libpostal.so.1  "$LIB_OUT/" 2>/dev/null || true
cp src/.libs/libpostal.dylib "$LIB_OUT/" 2>/dev/null || true

echo "==> Downloading model data (one-time, requires internet) …"
mkdir -p "$DATA_DIR"
./data/download.sh "$DATA_DIR"

echo ""
echo "Done! Next steps:"
echo "  python scripts/quantize_model.py  --src $DATA_DIR --dst address_finder/_data_raw"
echo "  python scripts/build_dawg.py      --datadir address_finder/_data_raw"
echo "  python scripts/compress_bundle.py"
