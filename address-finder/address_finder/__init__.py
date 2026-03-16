"""
address_finder — self-contained libpostal Python bindings.
Data is decompressed once to ~/.cache/address_finder/ on first import.
"""
from address_finder._init_data import ensure_data
from address_finder._lib_loader import init_libpostal, get_lib

# Decompress bundled data on first use, then cache forever
_DATADIR = ensure_data()
_LIB     = init_libpostal(_DATADIR)

from address_finder.parser   import parse_address
from address_finder.expander import expand_address

__all__ = ["parse_address", "expand_address"]
__version__ = "1.0.0"
