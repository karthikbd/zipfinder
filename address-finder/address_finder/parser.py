"""parse_address() — wraps libpostal_parse_address via ctypes."""
import ctypes
from typing import List, Tuple
from address_finder._lib_loader import get_lib, _ParseOptions

# Labels emitted by libpostal's CRF parser
LABELS = [
    "house", "house_number", "po_box", "building",
    "entrance", "staircase", "level", "unit",
    "road", "metro_station", "suburb", "city_district",
    "city", "island", "state_district", "state",
    "country_region", "country", "world_region",
    "postcode", "website", "telephone", "email",
    "attention", "care_of", "near", "intersection",
]


def parse_address(
    address: str,
    language: str | None = None,
    country: str  | None = None,
) -> List[Tuple[str, str]]:
    """
    Parse a raw address string into labeled components.

    Returns a list of (value, label) tuples, e.g.:
        [('781', 'house_number'), ('franklin ave', 'road'), ...]

    Parameters
    ----------
    address  : raw address string (any language/script)
    language : ISO 639-1 hint, e.g. 'en', 'fr', 'de' (optional)
    country  : ISO 3166-1 alpha-2 hint, e.g. 'us', 'de'  (optional)
    """
    lib = get_lib()
    opts = lib.libpostal_get_default_parse_options()
    if language:
        opts.language = language.encode()
    if country:
        opts.country = country.encode()

    num_components = ctypes.c_size_t(0)
    result_ptr = lib.libpostal_parse_address(
        address.encode("utf-8"),
        ctypes.byref(opts),
        ctypes.byref(num_components),
    )
    if not result_ptr:
        return []

    n = num_components.value
    # libpostal returns alternating value/label pairs
    pairs = []
    for i in range(n):
        value = result_ptr[i * 2].decode("utf-8")     if result_ptr[i * 2]     else ""
        label = result_ptr[i * 2 + 1].decode("utf-8") if result_ptr[i * 2 + 1] else ""
        pairs.append((value, label))

    lib.libpostal_address_parser_response_destroy(result_ptr, n)
    return pairs
