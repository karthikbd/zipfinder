"""
Load the bundled libpostal shared library via ctypes and wire up
all function signatures. No C compiler required at install time.
"""
import ctypes
import ctypes.util
import os
import sys
import pathlib
from importlib.resources import files as pkg_files

_lib_instance = None


def _find_bundled_lib() -> str:
    lib_dir = pkg_files("address_finder").joinpath("_libs")
    candidates = {
        "linux":  "libpostal.so.1",
        "darwin": "libpostal.1.dylib",
        "win32":  "postal.dll",
    }
    platform = sys.platform
    name = candidates.get(platform, "libpostal.so.1")
    path = pathlib.Path(str(lib_dir)) / name
    if not path.exists():
        # fallback: try system libpostal
        system = ctypes.util.find_library("postal")
        if system:
            return system
        raise FileNotFoundError(
            f"Bundled lib not found at {path}. "
            "Run 'bash scripts/build_libpostal.sh' first."
        )
    return str(path)


def init_libpostal(datadir: str) -> ctypes.CDLL:
    """Load shared lib, set up function sigs, init with bundled datadir."""
    global _lib_instance
    if _lib_instance is not None:
        return _lib_instance

    lib_path = _find_bundled_lib()
    lib = ctypes.cdll.LoadLibrary(lib_path)

    # ── setup / teardown ──────────────────────────────────────────
    lib.libpostal_setup.restype  = ctypes.c_bool
    lib.libpostal_setup.argtypes = []

    lib.libpostal_setup_datadir.restype  = ctypes.c_bool
    lib.libpostal_setup_datadir.argtypes = [ctypes.c_char_p]

    lib.libpostal_setup_parser_datadir.restype  = ctypes.c_bool
    lib.libpostal_setup_parser_datadir.argtypes = [ctypes.c_char_p]

    lib.libpostal_setup_language_classifier_datadir.restype  = ctypes.c_bool
    lib.libpostal_setup_language_classifier_datadir.argtypes = [ctypes.c_char_p]

    lib.libpostal_teardown.restype  = None
    lib.libpostal_teardown.argtypes = []

    # ── parser ────────────────────────────────────────────────────
    lib.libpostal_parse_address.restype  = ctypes.POINTER(ctypes.c_char_p)
    lib.libpostal_parse_address.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(_ParseOptions),
        ctypes.POINTER(ctypes.c_size_t),
    ]
    lib.libpostal_get_default_parse_options.restype  = _ParseOptions
    lib.libpostal_get_default_parse_options.argtypes = []

    lib.libpostal_address_parser_response_destroy.restype  = None
    lib.libpostal_address_parser_response_destroy.argtypes = [
        ctypes.POINTER(ctypes.c_char_p), ctypes.c_size_t
    ]

    # ── expander ──────────────────────────────────────────────────
    lib.libpostal_expand_address.restype  = ctypes.POINTER(ctypes.c_char_p)
    lib.libpostal_expand_address.argtypes = [
        ctypes.c_char_p,
        _NormalizeOptions,
        ctypes.POINTER(ctypes.c_size_t),
    ]
    lib.libpostal_get_default_options.restype  = _NormalizeOptions
    lib.libpostal_get_default_options.argtypes = []

    lib.libpostal_expansion_array_destroy.restype  = None
    lib.libpostal_expansion_array_destroy.argtypes = [
        ctypes.POINTER(ctypes.c_char_p), ctypes.c_size_t
    ]

    # ── initialize with bundled data dir (no HTTP, no S3) ─────────
    _data = datadir.encode("utf-8")
    ok = lib.libpostal_setup_datadir(_data)
    if not ok:
        raise RuntimeError(f"libpostal_setup_datadir failed for: {datadir}")
    lib.libpostal_setup_parser_datadir(_data)
    lib.libpostal_setup_language_classifier_datadir(_data)

    import atexit
    atexit.register(lib.libpostal_teardown)

    _lib_instance = lib
    return lib


def get_lib() -> ctypes.CDLL:
    if _lib_instance is None:
        raise RuntimeError("Call init_libpostal() first.")
    return _lib_instance


# ── ctypes structs matching libpostal.h ───────────────────────────────────
class _ParseOptions(ctypes.Structure):
    _fields_ = [
        ("language",    ctypes.c_char_p),
        ("country",     ctypes.c_char_p),
    ]

class _NormalizeOptions(ctypes.Structure):
    _fields_ = [
        ("languages",            ctypes.POINTER(ctypes.c_char_p)),
        ("num_languages",        ctypes.c_size_t),
        ("address_components",   ctypes.c_uint16),
        ("latin_ascii",          ctypes.c_bool),
        ("transliterate",        ctypes.c_bool),
        ("strip_accents",        ctypes.c_bool),
        ("decompose",            ctypes.c_bool),
        ("lowercase",            ctypes.c_bool),
        ("trim_string",          ctypes.c_bool),
        ("drop_parentheticals",  ctypes.c_bool),
        ("replace_numeric_hyphens", ctypes.c_bool),
        ("delete_numeric_hyphens",  ctypes.c_bool),
        ("split_alpha_from_numeric", ctypes.c_bool),
        ("replace_word_hyphens",    ctypes.c_bool),
        ("delete_word_hyphens",     ctypes.c_bool),
        ("delete_final_periods",    ctypes.c_bool),
        ("delete_acronym_periods",  ctypes.c_bool),
        ("drop_english_possessives", ctypes.c_bool),
        ("delete_apostrophes",      ctypes.c_bool),
        ("expand_numex",            ctypes.c_bool),
        ("roman_numerals",          ctypes.c_bool),
    ]
