#!/usr/bin/env python
"""
Step 4: Pack address_finder/_data_raw/ into address_finder/_data.tar.zst
using zstd level-22 (maximum compression).
Typical result: 130 MB quantized data → 40-55 MB compressed bundle.
"""
import tarfile, pathlib, zstandard as zstd

DATA_DIR = pathlib.Path("address_finder/_data_raw")
OUT_FILE = pathlib.Path("address_finder/_data.tar.zst")

if not DATA_DIR.exists():
    raise FileNotFoundError(
        f"{DATA_DIR} not found. Run quantize_model.py first."
    )

print(f"Compressing {DATA_DIR} → {OUT_FILE} …")
cctx = zstd.ZstdCompressor(
    level=22,
    threads=-1,
    write_content_size=True,
    write_checksum=True,
)

with open(OUT_FILE, "wb") as fh:
    with cctx.stream_writer(fh, closefd=False) as writer:
        with tarfile.open(fileobj=writer, mode="w|") as tar:
            tar.add(DATA_DIR, arcname="postal_data")

size_mb = OUT_FILE.stat().st_size / 1e6
print(f"Done. Bundle size: {size_mb:.1f} MB")
if size_mb > 100:
    print("WARNING: bundle exceeds PyPI 100 MB limit.")
    print("Consider using the split-package fallback (see README).")
else:
    print("Bundle fits within PyPI 100 MB limit.")
