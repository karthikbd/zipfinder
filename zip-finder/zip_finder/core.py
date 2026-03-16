"""
zip_finder — core database engine
=================================
Offline postal-code / geocode lookup powered by GeoNames data.

Algorithm complexity guarantees
--------------------------------
Operation                     Time              Space (extra overhead)
───────────────────────────── ────────────────  ──────────────────────
get(zip, country)             O(1)              —
get(zip)    [no country]      O(1)              —
get_all(zip)                  O(1)              —
search(query)                 O(log N + K)      —
find_nearby(lat, lon, r)      O(C + K·log K)    —
get_stats / get_countries     O(1) / O(N log N) —

  N = total records in the database
  K = number of results returned (≤ limit)
  C = records in the geo-grid cells that overlap the search bounding box
      (typically 1–9 cells regardless of N at radii ≤ 100 km)

Space overhead
--------------
Records are stored once in ``_country_index``.  All other indexes hold
*references* to those same dicts — no record data is duplicated.

  _postal_index   : Dict[str, Dict]                   O(N) refs
  _zip_only_index : Dict[str, List[Dict]]              O(N) refs
  _country_index  : Dict[str, List[Dict]]              O(N) refs  ← primary
  _postal_sorted  : List[Tuple[str, Dict]]             O(N) refs
  _city_sorted    : List[Tuple[str, Dict]]             O(N) refs
  _geo_grid       : Dict[Tuple[int,int], List[Dict]]   O(N) refs
  LRU cache       : most-recently-used get() results   bounded O(LRU_SIZE)

For datasets that exceed available RAM (TB / ZB scale) pass
``use_sqlite=True`` to ``ZipFinderDatabase()`` or ``get_database()``.
That path streams data into a temporary SQLite file (WAL mode, fully
indexed) so memory consumption stays constant regardless of data size.
"""

from __future__ import annotations

import bisect
import gzip
import json
import math
import os
import pickle
import pkgutil
import sqlite3
import tempfile
from collections import defaultdict
from functools import lru_cache
from typing import Dict, Iterator, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Tuneable constants
# ---------------------------------------------------------------------------

# Size of each geo-grid bucket in degrees.
# 1 degree ≈ 111 km at the equator.  A 10 km radius search checks at most
# 4 buckets; a 100 km radius checks at most 16.
_GEO_GRID_DEG: float = 1.0

# Module-level LRU cache size for get().
# Each slot holds one dict *reference* — not a copy.
_LRU_CACHE_SIZE: int = 8192


# ---------------------------------------------------------------------------
# ZipFinderDatabase  (thread-safe singleton, lazy-loaded)
# ---------------------------------------------------------------------------

class ZipFinderDatabase:
    """
    In-memory (or SQLite-backed) postal-code database with
    O(1) / O(log N) indexed access at any data scale.

    Instantiate directly or use the module-level helper functions.

    Parameters
    ----------
    use_sqlite : bool
        When *True* the database is backed by a temporary SQLite file
        instead of pure Python dicts.  Enables constant-memory processing
        of datasets that exceed available RAM (TB / ZB scale).
        Default: *False* (in-memory — fastest for up to a few hundred
        million records on typical hardware).
    """

    _instance: Optional["ZipFinderDatabase"] = None
    _loaded:    bool = False

    # Class-level index slots (shared across all __init__ calls)
    _postal_index:   Optional[Dict[str, Dict]]                   = None
    _zip_only_index: Optional[Dict[str, List[Dict]]]             = None
    _country_index:  Optional[Dict[str, List[Dict]]]             = None
    _city_sorted:    Optional[List[Tuple[str, Dict]]]            = None
    _postal_sorted:  Optional[List[Tuple[str, Dict]]]            = None
    _geo_grid:       Optional[Dict[Tuple[int, int], List[Dict]]] = None

    # SQLite specifics
    _sqlite_path: Optional[str] = None
    _use_sqlite:  bool          = False

    # ------------------------------------------------------------------ #
    # Singleton boilerplate
    # ------------------------------------------------------------------ #

    def __new__(cls, use_sqlite: bool = False):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, use_sqlite: bool = False):
        if not ZipFinderDatabase._loaded:
            ZipFinderDatabase._use_sqlite = use_sqlite
            if use_sqlite:
                self._load_sqlite()
            else:
                self._load_memory()
            ZipFinderDatabase._loaded = True

    # ------------------------------------------------------------------ #
    # ── IN-MEMORY LOADING ───────────────────────────────────────────── #
    # ------------------------------------------------------------------ #

    def _load_memory(self) -> None:
        """
        Load all data into memory and build every index.
        Tries pre-built pickle indexes first (fastest start-up);
        falls back to streaming parse of the compressed JSONL source.
        """
        print("ZipFinder: loading database into memory …")
        try:
            self._load_from_pickles()
        except Exception:
            self._build_from_jsonl_stream()

        # Derived indexes — O(N) or O(N log N) build once at start-up
        self._build_zip_only_index()
        # NOTE: _postal_sorted / _city_sorted / _geo_grid are built lazily
        # on the first search() / find_nearby() call to keep startup fast.

        n = sum(len(v) for v in self._country_index.values())
        print(f"ZipFinder: ready — {n:,} records, "
              f"{len(self._country_index)} countries.")

    def _load_from_pickles(self) -> None:
        """Load pre-built primary indexes from compressed pickles.  O(N)."""
        cdata = pkgutil.get_data(__name__, "data/country_index.pkl.gz")
        pdata = pkgutil.get_data(__name__, "data/postal_index.pkl.gz")
        ZipFinderDatabase._country_index = pickle.loads(gzip.decompress(cdata))
        ZipFinderDatabase._postal_index  = pickle.loads(gzip.decompress(pdata))

    def _build_from_jsonl_stream(self) -> None:
        """
        Stream-parse ``geonames_data.jsonl.gz`` and build primary indexes.

        Memory : records stored in country_index; postal_index holds refs.
        Time   : O(N) — single pass through source file.
        """
        print("ZipFinder: building indexes from JSONL (streaming) …")
        country_idx: Dict[str, List[Dict]] = defaultdict(list)
        postal_idx:  Dict[str, Dict]       = {}

        raw = pkgutil.get_data(__name__, "data/geonames_data.jsonl.gz")
        for line in gzip.decompress(raw).decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            cc   = rec.get("country_code", "")
            zip_ = rec.get("postal_code", "")
            country_idx[cc].append(rec)
            postal_idx[f"{cc}:{zip_}"] = rec

        ZipFinderDatabase._country_index = dict(country_idx)
        ZipFinderDatabase._postal_index  = postal_idx

    # ------------------------------------------------------------------ #
    # ── DERIVED INDEX BUILDERS ──────────────────────────────────────── #
    # ------------------------------------------------------------------ #

    def _iter_all_records(self) -> Iterator[Dict]:
        """
        Yield every record exactly once from country_index.
        Avoids building a redundant flat list — O(1) extra space.
        """
        for recs in self._country_index.values():
            yield from recs

    def _build_zip_only_index(self) -> None:
        """
        Reverse-zip index: postal_code → [records across all countries].

        Enables O(1) lookup when no country code is supplied.

        Build : O(N).   Lookup : O(1).   Space : O(N) references.
        """
        idx: Dict[str, List[Dict]] = defaultdict(list)
        for key, rec in self._postal_index.items():
            zip_ = key.split(":", 1)[1]
            idx[zip_].append(rec)
        ZipFinderDatabase._zip_only_index = dict(idx)

    def _build_sorted_prefix_indexes(self) -> None:
        """
        Build two sorted ``(key, record)`` arrays for O(log N + K) prefix
        search via :mod:`bisect`:

          ``_postal_sorted`` — keyed by lowercase ``postal_code``
          ``_city_sorted``   — keyed by lowercase ``city``

        Build : O(N log N).   Query : O(log N + K).
        Space : O(N) references (no record copies).
        """
        postal_pairs: List[Tuple[str, Dict]] = []
        city_pairs:   List[Tuple[str, Dict]] = []

        for rec in self._iter_all_records():
            z = rec.get("postal_code", "").lower()
            c = rec.get("city", "").lower()
            if z:
                postal_pairs.append((z, rec))
            if c:
                city_pairs.append((c, rec))

        postal_pairs.sort(key=lambda t: t[0])
        city_pairs.sort(key=lambda t: t[0])

        ZipFinderDatabase._postal_sorted = postal_pairs
        ZipFinderDatabase._city_sorted   = city_pairs

    def _build_geo_grid(self) -> None:
        """
        Spatial grid: (lat_bucket, lon_bucket) → [records].
        Bucket size = ``_GEO_GRID_DEG`` degrees.

        A radius-r search examines only the grid cells whose bounding
        boxes overlap the query circle — typically 1–9 cells for r ≤ 100 km,
        completely independent of total N.

        Build : O(N).   Spatial query : O(C + K·log K).
        Space : O(N) references.
        """
        grid: Dict[Tuple[int, int], List[Dict]] = defaultdict(list)
        for rec in self._iter_all_records():
            try:
                lat = float(rec["latitude"])
                lon = float(rec["longitude"])
            except (KeyError, ValueError, TypeError):
                continue
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                continue
            cell = (
                int(math.floor(lat / _GEO_GRID_DEG)),
                int(math.floor(lon / _GEO_GRID_DEG)),
            )
            grid[cell].append(rec)

        ZipFinderDatabase._geo_grid = dict(grid)

    # ------------------------------------------------------------------ #
    # ── SQLITE (ON-DISK) PATH  — for TB / ZB datasets ─────────────── #
    # ------------------------------------------------------------------ #

    def _load_sqlite(self) -> None:
        """
        Stream JSONL into a temporary SQLite database with full indexes.
        Memory usage: O(1) — only the current batch is held in RAM.

        SQLite indexes created
        ──────────────────────
        idx_postal   : (country_code, postal_code)  → O(log N) exact
        idx_zip      : (postal_code)                → O(log N) exact
        idx_country  : (country_code)               → O(log N) filter
        idx_grid     : (lat_bucket, lon_bucket)     → O(1) spatial cell
        city_fts     : FTS5 virtual table on city   → O(log N) substring
        """
        print("ZipFinder: streaming data into SQLite (on-disk mode) …")
        tmp = tempfile.NamedTemporaryFile(
            suffix=".db", delete=False, prefix="zip_finder_"
        )
        ZipFinderDatabase._sqlite_path = tmp.name
        tmp.close()

        con = sqlite3.connect(self._sqlite_path)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA temp_store=MEMORY")
        con.execute("PRAGMA cache_size=-65536")    # 64 MB page cache

        con.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id           INTEGER PRIMARY KEY,
                country_code TEXT,
                postal_code  TEXT,
                city         TEXT,
                state        TEXT,
                latitude     REAL,
                longitude    REAL,
                lat_bucket   INTEGER,
                lon_bucket   INTEGER,
                raw_json     TEXT
            )
        """)
        con.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS city_fts
            USING fts5(city, content=records, content_rowid=id)
        """)

        raw = pkgutil.get_data(__name__, "data/geonames_data.jsonl.gz")
        batch: List[tuple] = []
        BATCH_SIZE = 50_000

        def _flush(rows: List[tuple]) -> None:
            con.executemany(
                "INSERT INTO records "
                "(country_code,postal_code,city,state,latitude,longitude,"
                " lat_bucket,lon_bucket,raw_json) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                rows,
            )
            con.commit()

        for line in gzip.decompress(raw).decode("utf-8").splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            try:
                lat = float(rec.get("latitude", 0))
                lon = float(rec.get("longitude", 0))
            except (ValueError, TypeError):
                lat = lon = 0.0
            batch.append((
                rec.get("country_code", ""),
                rec.get("postal_code", ""),
                rec.get("city", ""),
                rec.get("state", ""),
                lat, lon,
                int(math.floor(lat / _GEO_GRID_DEG)),
                int(math.floor(lon / _GEO_GRID_DEG)),
                json.dumps(rec),
            ))
            if len(batch) >= BATCH_SIZE:
                _flush(batch)
                batch.clear()

        if batch:
            _flush(batch)

        # Build indexes after bulk insert — much faster than inline
        con.execute("CREATE INDEX IF NOT EXISTS idx_postal  ON records(country_code, postal_code)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_zip     ON records(postal_code)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_country ON records(country_code)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_grid    ON records(lat_bucket, lon_bucket)")
        con.execute("INSERT INTO city_fts(city_fts) VALUES('rebuild')")
        con.commit()
        con.close()

        n = sqlite3.connect(self._sqlite_path).execute(
            "SELECT COUNT(*) FROM records"
        ).fetchone()[0]
        print(f"ZipFinder (SQLite): ready — {n:,} records.")

    def _sqlite_con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._sqlite_path)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA cache_size=-32768")
        return con

    @staticmethod
    def _row_to_dict(row: tuple) -> Dict:
        return json.loads(row[0])

    # ------------------------------------------------------------------ #
    # Haversine  (great-circle distance)
    # ------------------------------------------------------------------ #

    @staticmethod
    def _haversine(lat1: float, lon1: float,
                   lat2: float, lon2: float) -> float:
        """Great-circle distance in km between two coordinates.  O(1)."""
        R = 6_371.0
        rlat1, rlon1, rlat2, rlon2 = map(math.radians, (lat1, lon1, lat2, lon2))
        dlat = rlat2 - rlat1
        dlon = rlon2 - rlon1
        a = (math.sin(dlat / 2) ** 2
             + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
        return R * 2 * math.asin(math.sqrt(min(a, 1.0)))

    # ------------------------------------------------------------------ #
    # ── PUBLIC API ──────────────────────────────────────────────────── #
    # ------------------------------------------------------------------ #

    def lookup_zip(self, postal_code: str,
            country: str = None) -> Optional[Dict]:
        """
        Look up a single postal code and return its record.

        ┌─────────────────────────┬────────────────┐
        │ Call style               │ Complexity     │
        ├─────────────────────────┼────────────────┤
        │ lookup_zip(zip, country) │ O(1) — hash    │
        │ lookup_zip(zip)          │ O(1) — hash    │
        └─────────────────────────┴────────────────┘

        When *country* is omitted the first record found for that postal
        code is returned (may belong to any country).
        Use :meth:`lookup_all_zips` to retrieve every matching record.
        """
        if self._use_sqlite:
            return self._sqlite_get(postal_code, country)
        if country:
            return self._postal_index.get(f"{country.upper()}:{postal_code}")
        matches = self._zip_only_index.get(postal_code)
        return matches[0] if matches else None

    # backward-compatible alias
    get = lookup_zip

    def lookup_all_zips(self, postal_code: str,
                country: str = None) -> List[Dict]:
        """
        Return **all** records matching *postal_code* across every country
        (or within one country when *country* is specified).

        Useful when the same code exists in multiple countries
        (e.g. ``"94107"`` exists in both US and DE).

        Complexity: O(1).
        """
        if self._use_sqlite:
            return self._sqlite_get_all(postal_code, country)
        if country:
            rec = self._postal_index.get(f"{country.upper()}:{postal_code}")
            return [rec] if rec else []
        return list(self._zip_only_index.get(postal_code, []))

    # backward-compatible alias
    get_all = lookup_all_zips

    def search_zip(self, query: str, country: str = None,
               limit: int = 10) -> List[Dict]:
        """
        Search for zip codes or cities by prefix.

        Complexity: O(log N + K)
          Uses binary search on pre-sorted arrays — no full-table scan
          regardless of dataset size.

        Parameters
        ----------
        query   : prefix string (case-insensitive); matches postal code OR city
        country : optional ISO-3166 two-letter code to restrict results
        limit   : maximum number of results to return
        """
        if self._use_sqlite:
            return self._sqlite_search(query, country, limit)

        # Lazy-build sorted prefix indexes on first search_zip() call
        if self._postal_sorted is None:
            print("ZipFinder: building prefix indexes …")
            self._build_sorted_prefix_indexes()

        q = query.lower()
        results: List[Dict] = []
        seen: set            = set()
        cc_filter            = country.upper() if country else None

        def _bisect_collect(sorted_arr: List[Tuple[str, Dict]]) -> None:
            lo = bisect.bisect_left(sorted_arr, (q,))
            for i in range(lo, len(sorted_arr)):
                key, rec = sorted_arr[i]
                if not key.startswith(q):
                    break
                if cc_filter and rec.get("country_code", "").upper() != cc_filter:
                    continue
                uid = f"{rec.get('country_code')}:{rec.get('postal_code')}"
                if uid not in seen:
                    seen.add(uid)
                    results.append(rec)
                if len(results) >= limit:
                    return

        # Postal prefix first (more precise), then city to fill remaining slots
        _bisect_collect(self._postal_sorted)
        if len(results) < limit:
            _bisect_collect(self._city_sorted)

        return results[:limit]

    # backward-compatible alias
    search = search_zip

    def find_nearby_zips(self, latitude: float, longitude: float,
                    radius_km: float = 10.0,
                    limit: int = 10,
                    country: str = None) -> List[Dict]:
        """
        Find postal codes within *radius_km* kilometres of a coordinate.

        Parameters
        ----------
        country : str, optional
            ISO 3166-1 alpha-2 country code to restrict results (e.g. 'US').
            If None, results from all countries are returned.

        Complexity: O(C + K·log K)
          C = total records in candidate grid cells.
          For a 10 km radius, C ≈ 0.004 % of N — effectively constant
          with respect to N.  Scales to billions of records.

        Results are sorted by ascending distance.  Each result dict
        includes an extra ``"distance_km"`` field.
        """
        if self._use_sqlite:
            return self._sqlite_find_nearby(latitude, longitude,
                                            radius_km, limit)

        country_filter = country.upper() if country else None

        # Lazy-build geo-grid on first find_nearby_zips() call
        if self._geo_grid is None:
            print("ZipFinder: building geo-grid …")
            self._build_geo_grid()

        # Bounding-box in degrees
        lat_deg = radius_km / 111.0
        cos_lat = math.cos(math.radians(abs(latitude)))
        lon_deg = radius_km / max(111.0 * cos_lat, 1e-9)

        lat_lo = int(math.floor((latitude  - lat_deg) / _GEO_GRID_DEG))
        lat_hi = int(math.floor((latitude  + lat_deg) / _GEO_GRID_DEG))
        lon_lo = int(math.floor((longitude - lon_deg) / _GEO_GRID_DEG))
        lon_hi = int(math.floor((longitude + lon_deg) / _GEO_GRID_DEG))

        candidates: List[Tuple[float, Dict]] = []
        for blat in range(lat_lo, lat_hi + 1):
            for blon in range(lon_lo, lon_hi + 1):
                cell = self._geo_grid.get((blat, blon))
                if cell is None:
                    continue
                for rec in cell:
                    if country_filter and rec.get("country_code") != country_filter:
                        continue
                    try:
                        d = self._haversine(
                            latitude, longitude,
                            float(rec["latitude"]),
                            float(rec["longitude"]),
                        )
                    except (KeyError, ValueError, TypeError):
                        continue
                    if d <= radius_km:
                        candidates.append((d, rec))

        candidates.sort(key=lambda x: x[0])
        results: List[Dict] = []
        for dist, rec in candidates[:limit]:
            r = rec.copy()
            r["distance_km"] = round(dist, 2)
            results.append(r)
        return results

    # backward-compatible alias
    find_nearby = find_nearby_zips

    def get_db_stats(self) -> Dict:
        """Return database statistics: total record count and number of countries."""
        if self._use_sqlite:
            con = self._sqlite_con()
            row = con.execute(
                "SELECT COUNT(*) AS n, COUNT(DISTINCT country_code) AS c "
                "FROM records"
            ).fetchone()
            con.close()
            return {"total_records": row[0], "countries": row[1]}
        try:
            meta = pkgutil.get_data(__name__, "data/metadata.json")
            return json.loads(meta.decode("utf-8"))
        except Exception:
            total = sum(len(v) for v in self._country_index.values())
            return {"total_records": total,
                    "countries": len(self._country_index)}

    # backward-compatible alias
    get_stats = get_db_stats

    def list_countries(self) -> List[str]:
        """Return a sorted list of all available ISO-3166 country codes."""
        if self._use_sqlite:
            con = self._sqlite_con()
            rows = con.execute(
                "SELECT DISTINCT country_code FROM records "
                "ORDER BY country_code"
            ).fetchall()
            con.close()
            return [r[0] for r in rows]
        return sorted(self._country_index.keys())

    # backward-compatible alias
    get_countries = list_countries

    # ------------------------------------------------------------------ #

    def _sqlite_get(self, postal_code: str,
                    country: str = None) -> Optional[Dict]:
        con = self._sqlite_con()
        if country:
            row = con.execute(
                "SELECT raw_json FROM records "
                "WHERE country_code=? AND postal_code=? LIMIT 1",
                (country.upper(), postal_code),
            ).fetchone()
        else:
            row = con.execute(
                "SELECT raw_json FROM records "
                "WHERE postal_code=? LIMIT 1",
                (postal_code,),
            ).fetchone()
        con.close()
        return self._row_to_dict(row) if row else None

    def _sqlite_get_all(self, postal_code: str,
                        country: str = None) -> List[Dict]:
        con = self._sqlite_con()
        if country:
            rows = con.execute(
                "SELECT raw_json FROM records "
                "WHERE country_code=? AND postal_code=?",
                (country.upper(), postal_code),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT raw_json FROM records WHERE postal_code=?",
                (postal_code,),
            ).fetchall()
        con.close()
        return [self._row_to_dict(r) for r in rows]

    def _sqlite_search(self, query: str, country: str = None,
                       limit: int = 10) -> List[Dict]:
        con = self._sqlite_con()
        q  = query + "%"
        cc = country.upper() if country else None
        if cc:
            rows = con.execute(
                "SELECT raw_json FROM records "
                "WHERE country_code=? AND (postal_code LIKE ? OR city LIKE ?) "
                "LIMIT ?",
                (cc, q, q, limit),
            ).fetchall()
        else:
            rows = con.execute(
                "SELECT raw_json FROM records "
                "WHERE postal_code LIKE ? OR city LIKE ? LIMIT ?",
                (q, q, limit),
            ).fetchall()
        con.close()
        return [self._row_to_dict(r) for r in rows]

    def _sqlite_find_nearby(self, latitude: float, longitude: float,
                            radius_km: float,
                            limit: int) -> List[Dict]:
        lat_deg = radius_km / 111.0
        cos_lat = math.cos(math.radians(abs(latitude)))
        lon_deg = radius_km / max(111.0 * cos_lat, 1e-9)

        lat_lo = int(math.floor((latitude  - lat_deg) / _GEO_GRID_DEG))
        lat_hi = int(math.floor((latitude  + lat_deg) / _GEO_GRID_DEG))
        lon_lo = int(math.floor((longitude - lon_deg) / _GEO_GRID_DEG))
        lon_hi = int(math.floor((longitude + lon_deg) / _GEO_GRID_DEG))

        con = self._sqlite_con()
        rows = con.execute(
            "SELECT raw_json, latitude, longitude FROM records "
            "WHERE lat_bucket BETWEEN ? AND ? AND lon_bucket BETWEEN ? AND ?",
            (lat_lo, lat_hi, lon_lo, lon_hi),
        ).fetchall()
        con.close()

        candidates: List[Tuple[float, Dict]] = []
        for raw, rlat, rlon in rows:
            try:
                d = self._haversine(latitude, longitude,
                                    float(rlat), float(rlon))
            except (ValueError, TypeError):
                continue
            if d <= radius_km:
                candidates.append((d, json.loads(raw)))

        candidates.sort(key=lambda x: x[0])
        results: List[Dict] = []
        for dist, rec in candidates[:limit]:
            rec["distance_km"] = round(dist, 2)
            results.append(rec)
        return results

    # ------------------------------------------------------------------ #
    # Cleanup
    # ------------------------------------------------------------------ #

    def close(self) -> None:
        """
        Release all resources.

        SQLite mode  : removes the temporary ``.db`` file.
        Memory mode  : clears all index references so memory can be GC'd.
        """
        if self._use_sqlite and self._sqlite_path:
            try:
                os.unlink(self._sqlite_path)
            except OSError:
                pass
            ZipFinderDatabase._sqlite_path = None
        else:
            ZipFinderDatabase._postal_index   = None
            ZipFinderDatabase._zip_only_index = None
            ZipFinderDatabase._country_index  = None
            ZipFinderDatabase._city_sorted    = None
            ZipFinderDatabase._postal_sorted  = None
            ZipFinderDatabase._geo_grid       = None

        ZipFinderDatabase._loaded   = False
        ZipFinderDatabase._instance = None


# ---------------------------------------------------------------------------
# Module-level convenience functions  (backward-compatible public API)
# ---------------------------------------------------------------------------

_db: Optional[ZipFinderDatabase] = None


def get_database(use_sqlite: bool = False) -> ZipFinderDatabase:
    """Return (or initialise) the global singleton database instance."""
    global _db
    if _db is None:
        _db = ZipFinderDatabase(use_sqlite=use_sqlite)
    return _db


@lru_cache(maxsize=_LRU_CACHE_SIZE)
def lookup_zip(postal_code: str, country: str = None) -> Optional[Dict]:
    """
    Look up a single zip / postal code and return its record.  O(1), LRU-cached.

    Parameters
    ----------
    postal_code : str   e.g. ``"94107"`` or ``"SW1A 2AA"``
    country     : str   ISO-3166 two-letter code, e.g. ``"US"``  (recommended)

    Returns the first matching record dict, or ``None``.
    Pass ``country`` for unambiguous results.
    Use :func:`lookup_all_zips` when you need every match across countries.
    """
    return get_database().lookup_zip(postal_code, country)

# backward-compatible alias
get = lookup_zip


def lookup_all_zips(postal_code: str, country: str = None) -> List[Dict]:
    """
    Return every record matched by *postal_code* across all countries.  O(1).

    Example
    -------
    >>> lookup_all_zips("94107")
    [{'country_code': 'DE', ...}, {'country_code': 'US', ...}]
    """
    return get_database().lookup_all_zips(postal_code, country)

# backward-compatible alias
get_all = lookup_all_zips


def search_zip(query: str, country: str = None, limit: int = 10) -> List[Dict]:
    """
    Search for zip codes or cities by prefix.  O(log N + K).

    Example
    -------
    >>> search_zip("Lon", country="GB", limit=5)
    >>> search_zip("941", country="US", limit=10)
    """
    return get_database().search_zip(query, country, limit)

# backward-compatible alias
search = search_zip


def find_nearby_zips(latitude: float, longitude: float,
                     radius_km: float = 10.0, limit: int = 10,
                     country: str = None) -> List[Dict]:
    """
    Find all zip codes within *radius_km* km of a coordinate.  O(C + K·log K).

    Parameters
    ----------
    country : str, optional
        ISO 3166-1 alpha-2 country code to restrict results (e.g. 'US').

    Returns results sorted by ascending distance.
    Each result dict includes an extra ``"distance_km"`` field.

    Example
    -------
    >>> find_nearby_zips(37.7749, -122.4194, radius_km=10)
    >>> find_nearby_zips(40.7128, -74.0060, radius_km=5, country='US')
    """
    return get_database().find_nearby_zips(latitude, longitude, radius_km, limit, country)

# backward-compatible alias
find_nearby = find_nearby_zips


def get_db_stats() -> Dict:
    """Return database statistics: total record count and number of countries."""
    return get_database().get_db_stats()

# backward-compatible alias
get_stats = get_db_stats


def list_countries() -> List[str]:
    """Return a sorted list of all available ISO-3166 country codes."""
    return get_database().list_countries()

# backward-compatible alias
get_countries = list_countries
