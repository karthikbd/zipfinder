"""
zip_finder — offline postal-code / geocode lookup
=================================================
Complete offline postal-code database.  Works 100 %% offline — no internet required.

Quick start
-----------
>>> from zip_finder import lookup_zip, search_zip, find_nearby_zips, lookup_all_zips
>>> lookup_zip("94107", country="US")
{'city': 'San Francisco', ...}
>>> lookup_all_zips("94107")          # all countries that share this zip
>>> search_zip("Lon", country="GB", limit=5)
>>> find_nearby_zips(37.7749, -122.4194, radius_km=10)

For datasets larger than available RAM (TB / ZB scale) use SQLite mode::

    from zip_finder import get_database
    db = get_database(use_sqlite=True)
"""

from .core import (
    # Primary API (new names)
    lookup_zip,
    lookup_all_zips,
    search_zip,
    find_nearby_zips,
    get_db_stats,
    list_countries,
    get_database,
    ZipFinderDatabase,
    # Backward-compatible function aliases (old names still work)
    get,
    get_all,
    search,
    find_nearby,
    get_stats,
    get_countries,
)

__version__ = "2.0.1"
__all__ = [
    # Primary API
    "lookup_zip",
    "lookup_all_zips",
    "search_zip",
    "find_nearby_zips",
    "get_db_stats",
    "list_countries",
    "get_database",
    "ZipFinderDatabase",
    # Backward-compatible aliases
    "get",
    "get_all",
    "search",
    "find_nearby",
    "get_stats",
    "get_countries",
]