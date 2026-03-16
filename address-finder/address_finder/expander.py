"""expand_address() — wraps libpostal_expand_address via ctypes."""
import ctypes
from typing import List
from address_finder._lib_loader import get_lib, _NormalizeOptions


def expand_address(address: str, languages: List[str] | None = None) -> List[str]:
    """
    Normalize and expand an address string into canonical variants.

    Returns a deduplicated list of normalized forms, e.g.:
        expand_address('Quatre vingt douze R. de la Roquette')
        → ['92 rue de la roquette']

    Parameters
    ----------
    address   : raw address string
    languages : list of ISO 639-1 codes to hint the expander (optional)
    """
    lib  = get_lib()
    opts = lib.libpostal_get_default_options()

    if languages:
        arr_type = ctypes.c_char_p * len(languages)
        opts.languages     = arr_type(*[l.encode() for l in languages])
        opts.num_languages = len(languages)

    n_expansions = ctypes.c_size_t(0)
    result_ptr = lib.libpostal_expand_address(
        address.encode("utf-8"),
        opts,
        ctypes.byref(n_expansions),
    )
    if not result_ptr:
        return []

    expansions = [
        result_ptr[i].decode("utf-8")
        for i in range(n_expansions.value)
        if result_ptr[i]
    ]
    lib.libpostal_expansion_array_destroy(result_ptr, n_expansions)
    return expansions
