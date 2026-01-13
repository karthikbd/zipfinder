"""
bd-geocode-offline - Complete offline GeoNames postal code database
"""

from .core import (
    get,
    search,
    find_nearby,
    get_stats,
    get_countries,
    GeoNamesDatabase
)

__version__ = "1.0.0"
__all__ = ['get', 'search', 'find_nearby', 'get_stats', 'get_countries', 'GeoNamesDatabase']