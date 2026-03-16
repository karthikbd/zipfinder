# zipfinder

[![PyPI version](https://badge.fury.io/py/zipfinder.svg)](https://badge.fury.io/py/zipfinder)
[![Python versions](https://img.shields.io/pypi/pyversions/zipfinder.svg)](https://pypi.org/project/zipfinder/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![GitHub stars](https://img.shields.io/github/stars/karthikbd/zipfinder?style=social)](https://github.com/karthikbd/zipfinder)

Complete offline postal-code / geocode database for Python.
**Works 100 % offline  no internet connection required.**

## Features

-  **1.8 million records** — 121 countries, worldwide postal-code dataset
-  **O(1) lookups** — hash-indexed, constant time regardless of dataset size
-  **O(log N) prefix search** — bisect-based, no full-table scans ever
-  **Spatial radius search** — geo-grid index, O(C + K·log K)
-  **TB / ZB scale** — optional SQLite mode for datasets that exceed RAM
-  **Zero dependencies** — Python standard library only
-  **Fully embedded** — all data ships inside the package

## Installation

```bash
pip install zipfinder
```

## Quick Start

```python
from zip_finder import lookup_zip, lookup_all_zips, search_zip, find_nearby_zips

# Exact lookup  O(1)
record = lookup_zip("94107", country="US")
print(record["city"])          # San Francisco
print(record["latitude"])      # 37.7647

# Lookup without country  returns first match across all countries
record = lookup_zip("94107")

# All countries sharing the same code  O(1)
all_matches = lookup_all_zips("94107")
for r in all_matches:
    print(r["country_code"], r["city"])

# Prefix search by zip or city  O(log N + K)
results = search_zip("Lon", country="GB", limit=5)
for r in results:
    print(r["postal_code"], r["city"])

# Nearby zip codes by coordinates  O(C + Klog K)
nearby = find_nearby_zips(37.7749, -122.4194, radius_km=10, limit=5)
for r in nearby:
    print(r["city"], r["distance_km"], "km")
```

## API Reference

| Function | Description | Time Complexity |
|---|---|---|
| `lookup_zip(code, country=None)` | Single zip lookup, returns one record or `None` | **O(1)** |
| `lookup_all_zips(code, country=None)` | All records for a zip across countries | **O(1)** |
| `search_zip(query, country=None, limit=10)` | Prefix search by zip or city name | **O(log N + K)** |
| `find_nearby_zips(lat, lon, radius_km=10, limit=10)` | Radius search by coordinates | **O(C + Klog K)** |
| `get_db_stats()` | Total records and country count | **O(1)** |
| `list_countries()` | Sorted list of all ISO-3166 country codes | **O(1)** |
| `get_database(use_sqlite=False)` | Access the raw database singleton |  |

### Record format

Every returned dict contains:

```python
{
    "postal_code":   "94107",
    "city":          "San Francisco",
    "state":         "California",
    "state_code":    "CA",
    "country_code":  "US",
    "latitude":      37.7647,
    "longitude":     -122.4194,
    "accuracy":      4
}
```

Results from `find_nearby_zips` also include a `"distance_km"` field.

## Advanced Usage

### Database statistics

```python
from zip_finder import get_db_stats, list_countries

stats = get_db_stats()
print(f"Records : {stats['total_records']:,}")   # 1,826,607
print(f"Countries: {stats['countries']}")        # 121

countries = list_countries()
print(countries[:5])   # ['AD', 'AE', 'AI', 'AL', 'AR']
```

### TB / ZB scale  SQLite mode

For datasets that exceed available RAM:

```python
from zip_finder import get_database

db = get_database(use_sqlite=True)
record = db.lookup_zip("94107", country="US")
```

## Function Name Reference

All function names and their descriptions:

| Function | Description | Time Complexity |
|---|---|---|
| `lookup_zip(code, country=None)` | Single zip lookup, returns one record or `None` | **O(1)** |
| `lookup_all_zips(code, country=None)` | All records for a zip across countries | **O(1)** |
| `search_zip(query, country=None, limit=10)` | Prefix search by zip or city name | **O(log N + K)** |
| `find_nearby_zips(lat, lon, radius_km=10, limit=10)` | Radius search by coordinates | **O(C + K\u00b7log K)** |
| `get_db_stats()` | Total records and country count | **O(1)** |
| `list_countries()` | Sorted list of all ISO-3166 country codes | **O(1)** |
| `get_database(use_sqlite=False)` | Access the raw database singleton |  |

## Contributing

1. Fork  [https://github.com/karthikbd/zipfinder](https://github.com/karthikbd/zipfinder)
2. Create a branch: `git checkout -b feature/my-feature`
3. Run tests: `python -m pytest tests/ -v`
4. Push and open a Pull Request

## License

MIT  [Karthikeyan Balasundaram](https://github.com/karthikbd)
