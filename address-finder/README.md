# address-finder

A **fully self-contained** Python address parser built on libpostal.
- Zero HTTP/S3 calls at runtime
- Global model, quantized (int8) + zstd-22 compressed
- Works completely offline after install

## Install
```bash
pip install address-finder
```

## Usage
```python
from address_finder import parse_address, expand_address

parse_address("781 Franklin Ave Crown Heights Brooklyn NYC NY 11216 USA")
# [('781', 'house_number'), ('franklin ave', 'road'), ...]

expand_address("Quatre vingt douze R. de la Roquette")
# ['92 rue de la roquette', ...]
```

## Build from Source
```bash
# 1. Compile libpostal (Linux/Mac) or use WSL on Windows
bash scripts/build_libpostal.sh

# 2. Quantize model weights
python scripts/quantize_model.py --src /tmp/postal_raw --dst address_finder/_data_raw

# 3. Re-encode tries as DAWG (optional)
python scripts/build_dawg.py --datadir address_finder/_data_raw

# 4. Compress bundle
python scripts/compress_bundle.py

# 5. Build wheel
pip wheel . -w dist/
```

## Windows
See `scripts/build_windows.ps1` for step-by-step Windows build using WSL.
