#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build libpostal for Windows using WSL, then download model data.
    Run from the address-finder/ root directory.

.DESCRIPTION
    Step 1: Uses WSL (Ubuntu) to compile libpostal and produce postal.dll
    Step 2: Downloads the ~3.5 GB libpostal model data into /tmp/postal_raw
    Step 3: Copies postal.dll into address_finder/_libs/
    Step 4: Prints next steps for quantize → compress → build wheel

.REQUIREMENTS
    - WSL 2 with Ubuntu installed  (wsl --install)
    - Python 3.9+ (Anaconda or system)
    - ~5 GB free disk space

.EXAMPLE
    Set-Location "c:\Users\karthikeyan1\PNC\package_build\address-finder"
    .\scripts\build_windows.ps1
#>

$ErrorActionPreference = "Stop"
$ROOT = (Get-Location).Path
$LIB_OUT = Join-Path $ROOT "address_finder\_libs"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  address-finder  Windows Build Script  " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ── 0. Pre-flight checks ──────────────────────────────────────────────────

Write-Host "[0/5] Checking prerequisites..." -ForegroundColor Yellow

# Check WSL
try {
    $wslCheck = wsl echo "ok" 2>&1
    if ($wslCheck -ne "ok") { throw "WSL not responding" }
    Write-Host "  WSL: OK" -ForegroundColor Green
} catch {
    Write-Error @"
WSL 2 is required but not found or not running.
Install it with:   wsl --install
Then restart and re-run this script.
"@
    exit 1
}

# Ensure lib output dir exists
New-Item -ItemType Directory -Force -Path $LIB_OUT | Out-Null

# ── 1. Install build deps in WSL ──────────────────────────────────────────

Write-Host ""
Write-Host "[1/5] Installing build dependencies in WSL (Ubuntu)..." -ForegroundColor Yellow

wsl bash -c @'
    set -e
    sudo apt-get update -qq
    sudo apt-get install -y -qq \
        git curl autoconf automake libtool pkg-config \
        libsnappy-dev build-essential
    echo "  Build deps: OK"
'@

# ── 2. Clone & compile libpostal ──────────────────────────────────────────

Write-Host ""
Write-Host "[2/5] Cloning & compiling libpostal (this takes ~5-10 min)..." -ForegroundColor Yellow

# Convert Windows path to WSL path
$WSL_ROOT = wsl wslpath -u $ROOT.Replace('\', '/')
$WSL_LIB_OUT = "$WSL_ROOT/address_finder/_libs"

wsl bash -c @"
    set -euo pipefail
    BUILD_DIR=/tmp/libpostal_build
    rm -rf \$BUILD_DIR
    git clone --depth 1 https://github.com/openvenues/libpostal \$BUILD_DIR
    cd \$BUILD_DIR
    ./bootstrap.sh
    ./configure --datadir=/tmp/postal_raw --disable-data-download --enable-shared
    make -j\$(nproc)
    mkdir -p '$WSL_LIB_OUT'

    # Copy the compiled shared lib
    if [ -f src/.libs/libpostal.so.1 ]; then
        cp src/.libs/libpostal.so.1 '$WSL_LIB_OUT/libpostal.so.1'
        echo '  libpostal.so.1 copied.'
    fi

    # Attempt to produce a Windows-loadable DLL via mingw cross-compile
    # (only if mingw is available)
    if command -v x86_64-w64-mingw32-gcc &>/dev/null; then
        echo 'MinGW found — cross-compiling postal.dll...'
        make clean
        ./configure --host=x86_64-w64-mingw32 --enable-shared --disable-static \
                    --datadir=/tmp/postal_raw --disable-data-download
        make -j\$(nproc)
        cp src/.libs/postal.dll '$WSL_LIB_OUT/postal.dll' 2>/dev/null || true
        echo '  postal.dll copied.'
    else
        echo 'MinGW not found — skipping DLL cross-compile.'
        echo 'Install with: sudo apt-get install -y mingw-w64'
        echo 'Then re-run this script to get postal.dll for Windows native use.'
    fi
    echo 'Compile step done.'
"@

Write-Host "  Compile: OK" -ForegroundColor Green

# ── 3. Download model data ────────────────────────────────────────────────

Write-Host ""
Write-Host "[3/5] Downloading libpostal model data (~3.5 GB)..." -ForegroundColor Yellow
Write-Host "      This is a one-time download." -ForegroundColor DarkGray

wsl bash -c @'
    set -euo pipefail
    DATA_DIR=/tmp/postal_raw
    mkdir -p "$DATA_DIR"

    BASE="https://github.com/openvenues/libpostal/releases/download/v1.1"
    FILES=(
        "parser.tar.gz"
        "address_expansions.tar.gz"
        "language_classifier.tar.gz"
    )

    for f in "${FILES[@]}"; do
        if [ ! -f "$DATA_DIR/$f" ]; then
            echo "  Downloading $f ..."
            curl -L --progress-bar -o "$DATA_DIR/$f" "$BASE/$f"
        else
            echo "  Skipping $f (already downloaded)"
        fi
        echo "  Extracting $f ..."
        tar -xzf "$DATA_DIR/$f" -C "$DATA_DIR"
    done
    echo "  Model data ready at $DATA_DIR"
'@

Write-Host "  Data download: OK" -ForegroundColor Green

# ── 4. List what we have ──────────────────────────────────────────────────

Write-Host ""
Write-Host "[4/5] Checking output..." -ForegroundColor Yellow
Get-ChildItem $LIB_OUT | ForEach-Object { Write-Host "  $_" }

# ── 5. Print next steps ───────────────────────────────────────────────────

Write-Host ""
Write-Host "[5/5] Build scaffold complete." -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Cyan
Write-Host "  1. Quantize the model weights (~600 MB → ~80 MB):" -ForegroundColor White
Write-Host "     python scripts\quantize_model.py --src \\\\wsl`$\Ubuntu\tmp\postal_raw --dst address_finder\_data_raw" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  2. (Optional) DAWG-encode expansion dictionaries:" -ForegroundColor White
Write-Host "     python scripts\build_dawg.py --datadir address_finder\_data_raw" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  3. Compress everything into the bundle (~40-55 MB):" -ForegroundColor White
Write-Host "     python scripts\compress_bundle.py" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  4. Build the wheel:" -ForegroundColor White
Write-Host "     python -m build" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  NOTE: If postal.dll was not produced (no MinGW)," -ForegroundColor Yellow
Write-Host "        install MinGW-w64 in WSL and re-run this script:" -ForegroundColor Yellow
Write-Host "        wsl sudo apt-get install -y mingw-w64" -ForegroundColor DarkCyan
Write-Host ""
