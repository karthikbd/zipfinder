"""
Decompress the bundled _data.tar.zst into ~/.cache/address_finder/
on first import. Subsequent imports are instant (stamp file check).
"""
import os
import tarfile
import pathlib
import logging
from importlib.resources import files as pkg_files

try:
    import zstandard as zstd
except ImportError as e:
    raise ImportError("zstandard is required: pip install zstandard") from e

log = logging.getLogger(__name__)

_VERSION   = "1.0.0"
_CACHE_DIR = pathlib.Path.home() / ".cache" / "address_finder" / _VERSION
_STAMP     = _CACHE_DIR / ".extracted"
_DATA_DIR  = _CACHE_DIR / "postal_data"


def ensure_data() -> str:
    """Return path to the extracted data dir, decompressing if needed."""
    if _STAMP.exists():
        log.debug("address_finder: using cached data at %s", _DATA_DIR)
        return str(_DATA_DIR)

    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    bundle = pkg_files("address_finder").joinpath("_data.tar.zst")

    log.info("address_finder: first-run extraction to %s …", _CACHE_DIR)
    dctx = zstd.ZstdDecompressor()
    with open(str(bundle), "rb") as fh:
        with dctx.stream_reader(fh) as reader:
            with tarfile.open(fileobj=reader, mode="r|") as tar:
                tar.extractall(str(_CACHE_DIR))

    _STAMP.touch()
    log.info("address_finder: extraction complete.")
    return str(_DATA_DIR)


def clear_cache():
    """Remove extracted data (forces re-extraction on next import)."""
    import shutil
    if _CACHE_DIR.exists():
        shutil.rmtree(_CACHE_DIR)
        print(f"Cache cleared: {_CACHE_DIR}")
