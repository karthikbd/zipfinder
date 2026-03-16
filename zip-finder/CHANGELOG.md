# Changelog

All notable changes to `zipfinder` are documented here.

## [2.0.0] - 2026-03-16  *(Renamed from bd-geocode-offline)*

### Breaking changes (backward-compatible aliases provided)
- Package renamed from `bd-geocode-offline` to `zipfinder` on PyPI
- Install with `pip install zipfinder`

### New API names (old names still work as aliases)
| Old | New |
|-----|-----|
| `get()` | `lookup_zip()` |
| `get_all()` | `lookup_all_zips()` |
| `search()` | `search_zip()` |
| `find_nearby()` | `find_nearby_zips()` |
| `get_stats()` | `get_db_stats()` |
| `get_countries()` | `list_countries()` |

### New features
- O(1) zip-only lookup (no country required) via `_zip_only_index`
- O(log N + K) prefix search with lazy-built bisect indexes
- Geo-grid spatial index, lazy-built on first `find_nearby_zips()` call
- SQLite mode for TB/ZB-scale datasets (`get_database(use_sqlite=True)`)
- LRU cache (8192 entries) on `lookup_zip()`
- Thread-safe singleton with `_loaded` guard

### Performance
- Startup time: ~5 s (pickle load)  sorted indexes built lazily
- `lookup_zip()`: O(1), ~0 ms after warm-up
- `search_zip()`: O(log N + K), <10 ms on 1.8 M records
- `find_nearby_zips()`: O(C + Klog K), <5 ms for 10 km radius

### Dataset
- 1,826,607 records across 121 countries (GeoNames full dump, 2025-03)

---

## [1.0.0] - 2024-01-01  *(as bd-geocode-offline)*

- Initial release as `bd-geocode-offline`
- Basic postal-code lookup using GeoNames data