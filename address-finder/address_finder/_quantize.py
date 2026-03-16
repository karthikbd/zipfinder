"""
Quantize libpostal's raw float64 weight arrays to int8 + per-row scale.
Run once at package build time (not at runtime).

Usage:
    python -m address_finder._quantize --src /tmp/postal_raw/address_parser \
                                       --dst address_finder/_data_raw/address_parser
"""
import struct
import pathlib
import argparse
import numpy as np


# ─── File format ──────────────────────────────────────────────────────────
# Original libpostal binary layout (averaged_perceptron.c):
#   [uint64 num_features][uint64 num_classes]
#   [float64 * num_features * num_classes]  ← we replace this section
#
# Quantized layout (my-postal extension):
#   [uint64 num_features][uint64 num_classes][uint8 QUANT_MAGIC=0xAB]
#   for each feature row i:
#       [float32 scale_i][int8 * num_classes]


QUANT_MAGIC = 0xAB  # marks quantized format


def quantize_perceptron(src_path: pathlib.Path, dst_path: pathlib.Path):
    """Convert a raw libpostal perceptron .bin file to quantized int8."""
    with open(src_path, "rb") as f:
        num_features = struct.unpack("<Q", f.read(8))[0]
        num_classes   = struct.unpack("<Q", f.read(8))[0]
        weights = np.frombuffer(
            f.read(num_features * num_classes * 8), dtype=np.float64
        ).reshape(num_features, num_classes).astype(np.float32)

    dst_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dst_path, "wb") as f:
        f.write(struct.pack("<Q", num_features))
        f.write(struct.pack("<Q", num_classes))
        f.write(struct.pack("<B", QUANT_MAGIC))
        for row in weights:
            max_abs = np.max(np.abs(row))
            scale   = float(max_abs / 127.0) if max_abs > 0 else 1e-8
            f.write(struct.pack("<f", scale))
            quantized = np.clip(np.round(row / scale), -127, 127).astype(np.int8)
            f.write(quantized.tobytes())

    orig_mb = src_path.stat().st_size / 1e6
    new_mb  = dst_path.stat().st_size / 1e6
    print(f"  {src_path.name}: {orig_mb:.1f} MB → {new_mb:.1f} MB "
          f"({100*new_mb/orig_mb:.0f}%)")


def dequantize_row(scale: float, quantized: np.ndarray) -> np.ndarray:
    """Restore float32 weights from an int8 row (used at inference time)."""
    return quantized.astype(np.float32) * scale


def quantize_directory(src_dir: str, dst_dir: str):
    src, dst = pathlib.Path(src_dir), pathlib.Path(dst_dir)
    for bin_file in src.rglob("*.bin"):
        rel  = bin_file.relative_to(src)
        out  = dst / rel
        print(f"Quantizing {rel} …")
        quantize_perceptron(bin_file, out)
    # copy all non-.bin files (tries, configs) unchanged
    import shutil
    for other in src.rglob("*"):
        if other.is_file() and other.suffix != ".bin":
            out = dst / other.relative_to(src)
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(other, out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True)
    ap.add_argument("--dst", required=True)
    args = ap.parse_args()
    quantize_directory(args.src, args.dst)
    print("Done.")
