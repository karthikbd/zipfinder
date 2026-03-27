# zipfinder

[![PyPI version](https://badge.fury.io/py/zipfinder.svg)](https://pypi.org/project/zipfinder/)
[![Python versions](https://img.shields.io/pypi/pyversions/zipfinder.svg)](https://pypi.org/project/zipfinder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/karthikbd/zipfinder/badge)](https://securityscorecards.dev/viewer/?uri=github.com/karthikbd/zipfinder)

Complete **offline** postal-code and geocode database for Python.
**Works 100% offline — no internet connection required at runtime.**

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [API Reference](#api-reference)
  - [lookup\_zip](#lookup_zipcode-countrynone)
  - [lookup\_all\_zips](#lookup_all_zipscode-countrynone)
  - [search\_zip](#search_zipquery-countrynone-limit10)
  - [find\_nearby\_zips](#find_nearby_zipslat-lon-radius_km10-limit10-countrynone)
  - [get\_db\_stats](#get_db_stats)
  - [list\_countries](#list_countries)
  - [get\_database](#get_databaseuse_sqlitefalse)
  - [Record Format](#record-format)
- [Backward-Compatible Aliases](#backward-compatible-aliases)
- [Advanced Usage](#advanced-usage)
- [Algorithm Complexity](#algorithm-complexity)
- [Data Source](#data-source)
- [Running Tests](#running-tests)
- [CI / CD](#ci--cd)
- [Security](#security)
- [Changelog](#changelog)
- [License](#license)

---

## Features

- **1.8 million records** — 121 countries, worldwide postal-code dataset sourced from GeoNames
- **O(1) lookups** — hash-indexed, constant time regardless of dataset size
- **O(log N) prefix search** — bisect-based, no full-table scans ever
- **Spatial radius search** — geo-grid index, O(C + K·log K)
- **TB / ZB scale** — optional SQLite mode for datasets that exceed available RAM
- **Zero dependencies** — Python standard library only
- **Fully embedded** — all data ships inside the package, no downloads needed
- **LRU cache** — 8 192-entry in-process cache on `lookup_zip()` for hot paths

---

## Installation

```bash
pip install zipfinder
```

Supports Python 3.7 through 3.12. No external dependencies.

---

## Quick Start

```python
from zip_finder import lookup_zip, lookup_all_zips, search_zip, find_nearby_zips

# Exact lookup — O(1)
record = lookup_zip("94107", country="US")
print(record["city"])        # San Francisco
print(record["latitude"])    # 37.7647
print(record["longitude"])   # -122.4194

# Lookup without country — returns first match across all countries
record = lookup_zip("94107")

# All records sharing the same postal code — O(1)
all_matches = lookup_all_zips("94107")
for r in all_matches:
    print(r["country_code"], r["city"])

# Prefix search by zip or city name — O(log N + K)
results = search_zip("Lon", country="GB", limit=5)
for r in results:
    print(r["postal_code"], r["city"])

# Nearby zip codes by coordinates — O(C + K·log K)
nearby = find_nearby_zips(37.7749, -122.4194, radius_km=10, limit=5)
for r in nearby:
    print(r["city"], r["distance_km"], "km")
```

---

## API Reference

### `lookup_zip(code, country=None)`

Look up a single postal code and return the first matching record.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | `str` | Postal / zip code to look up |
| `country` | `str \| None` | ISO 3166-1 alpha-2 country code (e.g. `"US"`, `"GB"`). If omitted, returns the first match across all countries. |

**Returns:** `dict | None` — a [record dict](#record-format) or `None` if not found.

**Complexity:** O(1) — hash lookup with LRU cache.

```python
lookup_zip("SW1A 2AA", country="GB")
# {'postal_code': 'SW1A 2AA', 'city': 'London', 'state': 'England',
#  'state_code': 'ENG', 'country_code': 'GB', 'latitude': 51.5033,
#  'longitude': -0.1269, 'accuracy': 6}
```

---

### `lookup_all_zips(code, country=None)`

Return **all** records matching the given postal code.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `code` | `str` | Postal / zip code |
| `country` | `str \| None` | Optional ISO country filter |

**Returns:** `list[dict]` — list of [record dicts](#record-format), empty list if not found.

**Complexity:** O(1).

```python
# "1000" appears in multiple countries
for r in lookup_all_zips("1000"):
    print(r["country_code"], r["city"])
# BE  Brussels
# MK  Skopje
# ...
```

---

### `search_zip(query, country=None, limit=10)`

Prefix search across both postal codes and city names.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `query` | `str` | Prefix string to search for |
| `country` | `str \| None` | Optional ISO country filter |
| `limit` | `int` | Maximum number of results (default `10`) |

**Returns:** `list[dict]` — list of [record dicts](#record-format).

**Complexity:** O(log N + K) where N = total records, K = results returned.

```python
# Search by city prefix
search_zip("Paris", country="FR", limit=3)
# [{'postal_code': '75001', 'city': 'Paris', ...},
#  {'postal_code': '75002', 'city': 'Paris', ...}, ...]

# Search by postal code prefix
search_zip("E1", country="GB", limit=5)
```

---

### `find_nearby_zips(lat, lon, radius_km=10, limit=10, country=None)`

Find postal codes within a radius of a coordinate.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `lat` | `float` | Latitude in decimal degrees |
| `lon` | `float` | Longitude in decimal degrees |
| `radius_km` | `float` | Search radius in kilometres (default `10`) |
| `limit` | `int` | Maximum number of results (default `10`) |
| `country` | `str \| None` | Optional ISO country filter |

**Returns:** `list[dict]` — [record dicts](#record-format) each with an additional `"distance_km"` field, sorted by distance ascending.

**Complexity:** O(C + K·log K) where C = records in overlapping geo-grid cells (typically 1–9 cells at ≤ 100 km radius, independent of N).

```python
nearby = find_nearby_zips(48.8566, 2.3522, radius_km=5, limit=10)
for r in nearby:
    print(f"{r['city']} ({r['postal_code']}) — {r['distance_km']:.2f} km")
# Paris (75001) — 0.37 km
# Paris (75004) — 0.92 km
# ...
```

---

### `get_db_stats()`

Return summary statistics about the loaded database.

**Returns:** `dict` with keys `total_records` (int) and `countries` (int).

```python
from zip_finder import get_db_stats

stats = get_db_stats()
print(f"Records:   {stats['total_records']:,}")  # 1,826,607
print(f"Countries: {stats['countries']}")        # 121
```

---

### `list_countries()`

Return a sorted list of all ISO 3166-1 alpha-2 country codes present in the database.

**Returns:** `list[str]`

**Complexity:** O(N log N) on first call (sorted once, then cached).

```python
from zip_finder import list_countries

countries = list_countries()
print(countries[:8])  # ['AD', 'AE', 'AI', 'AL', 'AR', 'AS', 'AT', 'AU']
print(len(countries)) # 121
```

---

### `get_database(use_sqlite=False)`

Access the underlying `ZipFinderDatabase` singleton directly.

**Parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `use_sqlite` | `bool` | If `True`, load data into a temporary SQLite file instead of RAM |

**Returns:** `ZipFinderDatabase` instance.

```python
from zip_finder import get_database

# In-memory (default)
db = get_database()

# SQLite-backed (for TB/ZB scale datasets)
db = get_database(use_sqlite=True)
record = db.lookup_zip("94107", country="US")
```

---

### Record Format

Every returned record is a plain `dict` with the following fields:

```python
{
    "postal_code":  "94107",       # str  — postal / zip code
    "city":         "San Francisco",# str  — place name
    "state":        "California",  # str  — full state / province name
    "state_code":   "CA",          # str  — state/province code
    "country_code": "US",          # str  — ISO 3166-1 alpha-2
    "latitude":     37.7647,       # float
    "longitude":    -122.4194,     # float
    "accuracy":     4              # int  — GeoNames accuracy level (1–6)
}
```

Results from `find_nearby_zips()` also include:

```python
    "distance_km":  2.34           # float — great-circle distance from query point
```

---

## Backward-Compatible Aliases

The v2.0.0 rename added clearer function names. The old names continue to work:

| Old name (v1.x) | New name (v2.x) |
|-----------------|-----------------|
| `get()` | `lookup_zip()` |
| `get_all()` | `lookup_all_zips()` |
| `search()` | `search_zip()` |
| `find_nearby()` | `find_nearby_zips()` |
| `get_stats()` | `get_db_stats()` |
| `get_countries()` | `list_countries()` |

---

## Advanced Usage

### Filter nearby results by country

```python
# Only return French zip codes near the Swiss border
nearby = find_nearby_zips(46.2, 6.15, radius_km=20, country="FR")
```

### Combine prefix search with country filter

```python
# All German zip codes starting with "10" (central Berlin)
results = search_zip("10", country="DE", limit=20)
```

### Iterate over all records for a country

```python
from zip_finder import get_database

db = get_database()
gb_records = db._country_index.get("GB", [])
print(f"UK records: {len(gb_records):,}")
```

### SQLite mode for large datasets

```python
from zip_finder import get_database

# Streams data to a temp SQLite file — constant RAM regardless of data size
db = get_database(use_sqlite=True)
record = db.lookup_zip("10115", country="DE")
```

---

## Algorithm Complexity

| Operation | Time | Notes |
|-----------|------|-------|
| `lookup_zip(code, country)` | **O(1)** | Hash index + LRU cache (8 192 entries) |
| `lookup_zip(code)` | **O(1)** | Zip-only hash index |
| `lookup_all_zips(code)` | **O(1)** | Hash index |
| `search_zip(query)` | **O(log N + K)** | Bisect on sorted prefix arrays |
| `find_nearby_zips(lat, lon, r)` | **O(C + K·log K)** | Geo-grid (1° cells), typically 1–9 cells |
| `get_db_stats()` | **O(1)** | Metadata cached at load time |
| `list_countries()` | **O(N log N)** first call, **O(1)** after | Sorted and cached |

**Space:** All indexes hold *references* to the same record dicts — no data duplication regardless of the number of indexes.

---

## Data Source

Postal code data sourced from [GeoNames](https://www.geonames.org/) (Creative Commons Attribution 4.0).
The embedded dataset covers **1.8 million records across 121 countries**.

To rebuild the dataset from fresh GeoNames exports:

```bash
python download_and_build.py
```

---

## Running Tests

```bash
pip install pytest
pytest tests/ -v
```

Test coverage includes:

- Exact lookup by code and country
- Lookup without country filter (cross-country)
- Prefix search by zip and city
- Spatial radius search with and without country filter
- Record structure validation
- Database stats and country listing
- SQLite mode
- Performance benchmarks (`tests/test_performance.py`)

---

## CI / CD

| Workflow | Trigger | Description |
|----------|---------|-------------|
| [Publish to PyPI](.github/workflows/python-publish.yml) | Push `v*.*.*` tag | Builds and publishes to PyPI |
| [OpenSSF Scorecard](.github/workflows/scorecard.yml) | Weekly + push to `main` | Security posture scan |

Dependabot is configured to keep Actions dependencies up to date
(see [`.github/dependabot.yml`](.github/dependabot.yml)).

---

## Security

Please review [SECURITY.md](SECURITY.md) for vulnerability reporting guidelines.
Do not open public GitHub issues for security vulnerabilities — use
[GitHub Security Advisories](https://github.com/karthikbd/zipfinder/security/advisories/new) instead.

---

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for the full version history.

---

## License

[MIT](LICENSE) © Karthikeyan Balasundaram

---

## Links

- **PyPI:** https://pypi.org/project/zipfinder/
- **Issues:** https://github.com/karthikbd/zipfinder/issues
- **GeoNames data:** https://www.geonames.org/
