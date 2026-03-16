#!/usr/bin/env python3
"""
Full build orchestrator for address-finder.
Run from the address-finder/ root directory.

Steps:
  1. Quantize model weights  (float64 → int8, ~600 MB → ~80 MB)
  2. Compress bundle          (zstd-22,      ~80 MB  → ~45 MB)
  3. Build wheel

Prerequisites:
  - libpostal data already downloaded to /tmp/postal_raw/
    (Linux/Mac: run scripts/build_libpostal.sh first)
    (Windows:   run scripts/build_windows.ps1 first)
  - postal.dll / libpostal.so.1 already in address_finder/_libs/
  - pip install build zstandard numpy

Usage:
    python scripts/build_package.py
    python scripts/build_package.py --skip-quantize   # if already done
    python scripts/build_package.py --data-dir /custom/path/to/postal_raw
"""

import argparse
import pathlib
import subprocess
import sys
import os

ROOT    = pathlib.Path(__file__).parent.parent.resolve()
LIB_DIR = ROOT / "address_finder" / "_libs"
DATA_RAW = ROOT / "address_finder" / "_data_raw"
BUNDLE  = ROOT / "address_finder" / "_data.tar.zst"

DEFAULT_DATA_DIR = pathlib.Path("/tmp/postal_raw")
if sys.platform == "win32":
    # Common WSL path on Windows
    DEFAULT_DATA_DIR = pathlib.Path(r"\\wsl$\Ubuntu\tmp\postal_raw")


def check_prereqs():
    print("\n[0] Checking prerequisites...")

    # Check _libs
    libs = list(LIB_DIR.glob("*.dll")) + list(LIB_DIR.glob("*.so*")) + \
           list(LIB_DIR.glob("*.dylib"))
    if not libs:
        print("  ERROR: No shared library found in address_finder/_libs/")
        print("  Run build_windows.ps1 (Windows) or build_libpostal.sh (Linux/Mac) first.")
        sys.exit(1)
    for lib in libs:
        print(f"  Found: {lib.name}  ({lib.stat().st_size / 1e6:.1f} MB)")

    # Check numpy
    try:
        import numpy
        print(f"  numpy: {numpy.__version__}  OK")
    except ImportError:
        print("  ERROR: numpy not installed.  Run: pip install numpy")
        sys.exit(1)

    # Check zstandard
    try:
        import zstandard
        print(f"  zstandard: {zstandard.__version__}  OK")
    except ImportError:
        print("  ERROR: zstandard not installed.  Run: pip install zstandard")
        sys.exit(1)

    print("  Prerequisites: OK")


def quantize(data_dir: pathlib.Path):
    print(f"\n[1] Quantizing model weights from {data_dir} ...")
    if not data_dir.exists():
        print(f"  ERROR: Data dir not found: {data_dir}")
        print("  Run build_windows.ps1 or build_libpostal.sh first to download data.")
        sys.exit(1)

    DATA_RAW.mkdir(parents=True, exist_ok=True)

    script = ROOT / "scripts" / "quantize_model.py"
    result = subprocess.run(
        [sys.executable, str(script), "--src", str(data_dir), "--dst", str(DATA_RAW)],
        check=False
    )
    if result.returncode != 0:
        print("  ERROR: quantize_model.py failed")
        sys.exit(1)

    size_mb = sum(f.stat().st_size for f in DATA_RAW.rglob("*") if f.is_file()) / 1e6
    print(f"  Quantized data size: {size_mb:.1f} MB")
    print("  Quantize: OK")


def compress():
    print(f"\n[2] Compressing bundle → {BUNDLE.name} ...")
    script = ROOT / "scripts" / "compress_bundle.py"
    result = subprocess.run([sys.executable, str(script)], check=False, cwd=str(ROOT))
    if result.returncode != 0:
        print("  ERROR: compress_bundle.py failed")
        sys.exit(1)

    size_mb = BUNDLE.stat().st_size / 1e6
    print(f"  Bundle: {size_mb:.1f} MB")
    if size_mb > 900:
        print("  WARNING: Bundle is large. Will not fit on public PyPI (100 MB limit).")
        print("           Upload to PNC Artifactory instead.")
    print("  Compress: OK")


def build_wheel():
    print("\n[3] Building wheel ...")
    result = subprocess.run(
        [sys.executable, "-m", "build", "--wheel"],
        check=False, cwd=str(ROOT)
    )
    if result.returncode != 0:
        print("  ERROR: wheel build failed. Run: pip install build")
        sys.exit(1)

    wheels = sorted((ROOT / "dist").glob("address_finder-*.whl"))
    if wheels:
        w = wheels[-1]
        size_mb = w.stat().st_size / 1e6
        print(f"  Built: {w.name}  ({size_mb:.1f} MB)")
    print("  Build wheel: OK")


def main():
    ap = argparse.ArgumentParser(description="Build address-finder wheel end-to-end")
    ap.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR),
                    help=f"Path to raw libpostal data (default: {DEFAULT_DATA_DIR})")
    ap.add_argument("--skip-quantize", action="store_true",
                    help="Skip quantization (if address_finder/_data_raw/ already built)")
    ap.add_argument("--skip-compress", action="store_true",
                    help="Skip compression (if address_finder/_data.tar.zst already built)")
    args = ap.parse_args()

    print("=" * 55)
    print("  address-finder  Full Build Pipeline")
    print("=" * 55)

    check_prereqs()

    if not args.skip_quantize:
        quantize(pathlib.Path(args.data_dir))
    else:
        print("\n[1] Skipping quantize (--skip-quantize)")

    if not args.skip_compress:
        compress()
    else:
        print("\n[2] Skipping compress (--skip-compress)")

    build_wheel()

    print("\n" + "=" * 55)
    print("  DONE")
    print("=" * 55)
    print("\nTo upload to PNC Artifactory:")
    print("  pip install twine")
    print("  twine upload --repository-url https://rpo.pncint.net/artifactory/api/pypi/rpo-pypi-release/ dist/address_finder-*.whl")


if __name__ == "__main__":
    main()
