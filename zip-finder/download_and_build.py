# download_and_build.py
"""
Script to download GeoNames postal code data and build zip_finder package
"""
import os
import sys
import json
import gzip
import zipfile
import shutil
import pandas as pd
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class ZipFinderPackageBuilder:
    """Build zip_finder package with embedded GeoNames data"""
    
    def __init__(self):
        self.base_dir = Path("zip-finder")
        self.source_dir = self.base_dir / "zip_finder"
        self.data_dir = self.source_dir / "data"
        self.download_dir = Path("geonames_downloads")
        
    def setup_directories(self):
        """Create necessary directories"""
        print("Setting up directories...")
        self.download_dir.mkdir(exist_ok=True)
        self.base_dir.mkdir(exist_ok=True)
        self.source_dir.mkdir(exist_ok=True)
        self.data_dir.mkdir(exist_ok=True)
        
        # Create examples directory
        (self.base_dir / "examples").mkdir(exist_ok=True)
        
        print("✓ Directories created")
    
    def download_essential_files(self):
        """
        Download essential GeoNames files.
        Returns: List of downloaded file paths
        """
        import urllib.request
        import ssl
        
        # Create unverified SSL context
        ssl_context = ssl._create_unverified_context()
        
        essential_files = [
            ("allCountries.zip", "https://download.geonames.org/export/zip/allCountries.zip"),
            ("readme.txt", "https://download.geonames.org/export/zip/readme.txt"),
            # Key country files
            ("US.zip", "https://download.geonames.org/export/zip/US.zip"),
            ("GB.zip", "https://download.geonames.org/export/zip/GB.zip"),
            ("IN.zip", "https://download.geonames.org/export/zip/IN.zip"),
            ("DE.zip", "https://download.geonames.org/export/zip/DE.zip"),
            ("FR.zip", "https://download.geonames.org/export/zip/FR.zip"),
            ("CN.zip", "https://download.geonames.org/export/zip/CN.zip"),
            ("JP.zip", "https://download.geonames.org/export/zip/JP.zip"),
            ("BR.zip", "https://download.geonames.org/export/zip/BR.zip"),
            ("RU.zip", "https://download.geonames.org/export/zip/RU.zip"),
            ("CA.zip", "https://download.geonames.org/export/zip/CA.zip"),
            ("AU.zip", "https://download.geonames.org/export/zip/AU.zip"),
        ]
        
        downloaded_files = []
        
        print("\nDownloading essential GeoNames files...")
        for filename, url in essential_files:
            filepath = self.download_dir / filename
            
            if filepath.exists():
                print(f"  ✓ {filename} already exists")
                downloaded_files.append(filepath)
                continue
                
            try:
                print(f"  Downloading {filename}...")
                urllib.request.urlretrieve(url, filepath, context=ssl_context)
                
                # Verify download
                if filepath.exists() and filepath.stat().st_size > 0:
                    size_kb = filepath.stat().st_size / 1024
                    print(f"    ✓ Downloaded ({size_kb:.1f} KB)")
                    downloaded_files.append(filepath)
                else:
                    print(f"    ✗ Download failed or empty")
                    
            except Exception as e:
                print(f"    ✗ Error downloading {filename}: {e}")
        
        print(f"\n✓ Downloaded {len(downloaded_files)} files")
        return downloaded_files
    
    def extract_and_process_data(self, zip_files):
        """Extract and process all ZIP files"""
        print("\nExtracting and processing data...")
        
        all_data = []
        
        # Process allCountries.zip first (main dataset)
        all_countries_zip = self.download_dir / "allCountries.zip"
        
        if all_countries_zip.exists():
            print("Processing allCountries.zip...")
            try:
                # Extract
                with zipfile.ZipFile(all_countries_zip, 'r') as zip_ref:
                    zip_ref.extractall(self.download_dir)
                
                # Read the extracted file
                all_countries_txt = self.download_dir / "allCountries.txt"
                if all_countries_txt.exists():
                    df = self.read_geonames_file(all_countries_txt)
                    if df is not None:
                        df['source'] = 'allCountries'
                        all_data.append(df)
                        print(f"  ✓ Added {len(df):,} records from allCountries")
            except Exception as e:
                print(f"  ✗ Error processing allCountries: {e}")
        
        # Process individual country files
        for zip_file in zip_files:
            if zip_file.name == "allCountries.zip":
                continue
                
            country_code = zip_file.stem.upper()
            print(f"Processing {country_code}.zip...")
            
            try:
                # Extract
                with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                    zip_ref.extractall(self.download_dir)
                
                # Look for extracted txt file
                txt_file = None
                for ext_file in self.download_dir.iterdir():
                    if ext_file.suffix == '.txt' and country_code in ext_file.name.upper():
                        txt_file = ext_file
                        break
                
                if txt_file and txt_file.exists():
                    df = self.read_geonames_file(txt_file)
                    if df is not None:
                        df['source'] = country_code
                        all_data.append(df)
                        print(f"  ✓ Added {len(df):,} records from {country_code}")
                        
            except Exception as e:
                print(f"  ✗ Error processing {country_code}: {e}")
                continue
        
        if not all_data:
            print("❌ No data was processed!")
            return None
        
        # Combine all data
        print("\nCombining all data...")
        combined_df = pd.concat(all_data, ignore_index=True)
        
        # Remove duplicates
        combined_df = combined_df.drop_duplicates(
            subset=['country_code', 'postal_code', 'place_name'],
            keep='first'
        )
        
        print(f"✓ Total unique records: {len(combined_df):,}")
        
        # Create slim version for embedding
        slim_df = combined_df[['country_code', 'postal_code', 'place_name',
                              'admin_name1', 'latitude', 'longitude']].copy()
        slim_df.rename(columns={
            'place_name': 'city',
            'admin_name1': 'state'
        }, inplace=True)
        
        # Fill NaN values
        slim_df = slim_df.fillna('')
        
        return slim_df
    
    def read_geonames_file(self, filepath):
        """Read a GeoNames text file"""
        try:
            df = pd.read_csv(
                filepath,
                sep='\t',
                header=None,
                encoding='utf-8',
                on_bad_lines='skip',
                names=[
                    'country_code', 'postal_code', 'place_name',
                    'admin_name1', 'admin_code1', 'admin_name2', 'admin_code2',
                    'admin_name3', 'admin_code3', 'latitude', 'longitude', 'accuracy'
                ]
            )
            return df
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                df = pd.read_csv(
                    filepath,
                    sep='\t',
                    header=None,
                    encoding='latin-1',
                    on_bad_lines='skip',
                    names=[
                        'country_code', 'postal_code', 'place_name',
                        'admin_name1', 'admin_code1', 'admin_name2', 'admin_code2',
                        'admin_name3', 'admin_code3', 'latitude', 'longitude', 'accuracy'
                    ]
                )
                return df
            except Exception as e:
                print(f"    ✗ Could not read {filepath.name}: {e}")
                return None
        except Exception as e:
            print(f"    ✗ Error reading {filepath.name}: {e}")
            return None
    
    def create_embedded_data_file(self, df):
        """Create compressed JSONL file for embedding"""
        print("\nCreating embedded data file...")
        
        data_file = self.data_dir / "geonames_data.jsonl.gz"
        
        with gzip.open(data_file, 'wt', encoding='utf-8') as f:
            for record in df.to_dict(orient='records'):
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        file_size_mb = data_file.stat().st_size / (1024 * 1024)
        print(f"✓ Created {data_file.name} ({len(df):,} records, {file_size_mb:.2f} MB)")
        
        return data_file
    
    def create_core_module(self):
        """Create the core.py module"""
        print("\nCreating core module...")
        
        core_content = '''"""
zip_finder core module
Offline GeoNames postal code database
"""
import gzip
import json
import pkgutil
import math
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from functools import lru_cache

@dataclass
class PostalCodeRecord:
    """Postal code record dataclass"""
    country_code: str
    postal_code: str
    city: str
    state: str
    latitude: float
    longitude: float
    
    def __post_init__(self):
        """Convert string coordinates to float"""
        try:
            self.latitude = float(self.latitude) if self.latitude else 0.0
            self.longitude = float(self.longitude) if self.longitude else 0.0
        except (ValueError, TypeError):
            self.latitude = 0.0
            self.longitude = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'country_code': self.country_code,
            'postal_code': self.postal_code,
            'city': self.city,
            'state': self.state,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

class GeoNamesDatabase:
    """
    Main GeoNames postal code database.
    Loads data from embedded compressed JSONL file.
    """
    
    _instance = None
    _data = None
    _country_index = None
    _postal_code_index = None
    _city_index = None
    
    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(GeoNamesDatabase, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize database (loads data on first access)"""
        if self._data is None:
            self._load_data()
    
    def _load_data(self):
        """Load data from embedded file"""
        print("Loading GeoNames postal code database...")
        
        self._data = []
        self._country_index = {}
        self._postal_code_index = {}
        self._city_index = {}
        
        # Load data from embedded file
        data_bytes = pkgutil.get_data('zip_finder', 'data/geonames_data.jsonl.gz')
        
        if not data_bytes:
            raise RuntimeError("Could not load embedded GeoNames data")
        
        # Parse compressed JSONL
        for line in gzip.decompress(data_bytes).decode('utf-8').splitlines():
            try:
                record_dict = json.loads(line)
                record = PostalCodeRecord(**record_dict)
                self._data.append(record)
                
                # Build indexes
                # Country index
                if record.country_code not in self._country_index:
                    self._country_index[record.country_code] = []
                self._country_index[record.country_code].append(record)
                
                # Postal code index (country + postal code as key)
                postal_key = f"{record.country_code}:{record.postal_code}"
                self._postal_code_index[postal_key] = record
                
                # City index (case-insensitive)
                city_key = f"{record.country_code}:{record.city.lower()}"
                if city_key not in self._city_index:
                    self._city_index[city_key] = []
                self._city_index[city_key].append(record)
                
            except (json.JSONDecodeError, TypeError) as e:
                continue
        
        print(f"✓ Loaded {len(self._data):,} postal code records")
        print(f"✓ Indexed {len(self._country_index)} countries")
    
    @property
    def total_records(self) -> int:
        """Total number of records"""
        return len(self._data) if self._data else 0
    
    @property
    def countries(self) -> List[str]:
        """List of available country codes"""
        return list(self._country_index.keys()) if self._country_index else []
    
    def get_postal_code(self, postal_code: str, country_code: str = None) -> Optional[PostalCodeRecord]:
        """
        Get postal code information.
        
        Args:
            postal_code: Postal code to search for
            country_code: Optional country code (recommended for faster lookup)
        
        Returns:
            PostalCodeRecord or None if not found
        """
        if country_code:
            # Fast lookup with country code
            key = f"{country_code.upper()}:{postal_code}"
            return self._postal_code_index.get(key)
        else:
            # Slower search across all countries
            for record in self._data:
                if record.postal_code == postal_code:
                    return record
            return None
    
    def search_city(self, city_name: str, country_code: str = None, limit: int = 10) -> List[PostalCodeRecord]:
        """
        Search for city by name.
        
        Args:
            city_name: City name (partial or full)
            country_code: Optional country code filter
            limit: Maximum results to return
        
        Returns:
            List of matching PostalCodeRecord objects
        """
        results = []
        city_lower = city_name.lower()
        
        if country_code:
            # Search within specific country
            country_code = country_code.upper()
            if country_code in self._country_index:
                for record in self._country_index[country_code]:
                    if city_lower in record.city.lower():
                        results.append(record)
                        if len(results) >= limit:
                            break
        else:
            # Search across all countries
            for record in self._data:
                if city_lower in record.city.lower():
                    results.append(record)
                    if len(results) >= limit:
                        break
        
        return results
    
    def get_country_postal_codes(self, country_code: str) -> List[PostalCodeRecord]:
        """
        Get all postal codes for a country.
        
        Args:
            country_code: ISO country code
        
        Returns:
            List of postal codes for the country
        """
        country_code = country_code.upper()
        return self._country_index.get(country_code, [])
    
    def find_nearby(self, latitude: float, longitude: float, radius_km: float = 10.0, 
                   limit: int = 10) -> List[Tuple[PostalCodeRecord, float]]:
        """
        Find postal codes near coordinates.
        
        Args:
            latitude: Latitude coordinate
            longitude: Longitude coordinate
            radius_km: Search radius in kilometers
            limit: Maximum results to return
        
        Returns:
            List of (PostalCodeRecord, distance_km) tuples
        """
        if not self._data:
            return []
        
        results = []
        
        for record in self._data:
            if record.latitude == 0.0 and record.longitude == 0.0:
                continue
            
            distance = self._haversine_distance(
                latitude, longitude,
                record.latitude, record.longitude
            )
            
            if distance <= radius_km:
                results.append((record, distance))
                if len(results) >= limit * 3:  # Get extras for sorting
                    break
        
        # Sort by distance and limit results
        results.sort(key=lambda x: x[1])
        return results[:limit]
    
    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculate distance between two coordinates using Haversine formula.
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
        
        Returns:
            Distance in kilometers
        """
        R = 6371.0  # Earth radius in kilometers
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def get_stats(self) -> Dict:
        """
        Get database statistics.
        
        Returns:
            Dictionary with statistics
        """
        stats = {
            'total_records': self.total_records,
            'total_countries': len(self.countries),
            'countries': {}
        }
        
        for country, records in self._country_index.items():
            stats['countries'][country] = len(records)
        
        return stats

# Singleton instance
_db_instance = None

def get_database() -> GeoNamesDatabase:
    """Get singleton database instance"""
    global _db_instance
    if _db_instance is None:
        _db_instance = GeoNamesDatabase()
    return _db_instance

# Convenience functions
@lru_cache(maxsize=1000)
def get_postal_code(postal_code: str, country_code: str = None) -> Optional[Dict]:
    """
    Get postal code information.
    
    Args:
        postal_code: Postal code to lookup
        country_code: Optional country code
    
    Returns:
        Dictionary with postal code info or None
    """
    db = get_database()
    record = db.get_postal_code(postal_code, country_code)
    return record.to_dict() if record else None

def search_city(city_name: str, country_code: str = None, limit: int = 10) -> List[Dict]:
    """
    Search for city by name.
    
    Args:
        city_name: City name to search
        country_code: Optional country code filter
        limit: Maximum results
    
    Returns:
        List of dictionaries with city information
    """
    db = get_database()
    records = db.search_city(city_name, country_code, limit)
    return [record.to_dict() for record in records]

def get_country_postal_codes(country_code: str) -> List[Dict]:
    """
    Get all postal codes for a country.
    
    Args:
        country_code: ISO country code
    
    Returns:
        List of postal code dictionaries
    """
    db = get_database()
    records = db.get_country_postal_codes(country_code)
    return [record.to_dict() for record in records]

def find_nearby(latitude: float, longitude: float, radius_km: float = 10.0, 
               limit: int = 10) -> List[Dict]:
    """
    Find postal codes near coordinates.
    
    Args:
        latitude: Latitude coordinate
        longitude: Longitude coordinate
        radius_km: Search radius in kilometers
        limit: Maximum results
    
    Returns:
        List of dictionaries with postal code info and distance
    """
    db = get_database()
    results = db.find_nearby(latitude, longitude, radius_km, limit)
    
    formatted_results = []
    for record, distance in results:
        result_dict = record.to_dict()
        result_dict['distance_km'] = round(distance, 2)
        formatted_results.append(result_dict)
    
    return formatted_results

def get_stats() -> Dict:
    """
    Get database statistics.
    
    Returns:
        Dictionary with statistics
    """
    db = get_database()
    return db.get_stats()

def get_countries() -> List[str]:
    """
    Get list of available country codes.
    
    Returns:
        List of country codes
    """
    db = get_database()
    return db.countries

# Export main functions
__all__ = [
    'get_postal_code',
    'search_city',
    'get_country_postal_codes',
    'find_nearby',
    'get_stats',
    'get_countries',
    'GeoNamesDatabase',
    'PostalCodeRecord'
]
'''
        
        with open(self.source_dir / "core.py", "w") as f:
            f.write(core_content)
        
        print("✓ Created core.py")
    
    def create_init_file(self):
        """Create __init__.py file"""
        print("\nCreating __init__.py...")
        
        init_content = '''"""
zip_finder
==========

Offline GeoNames postal code database for Python.

This package provides offline access to GeoNames postal code data,
including city names, states/provinces, and geographic coordinates.

Usage:
    >>> from zip_finder import get_postal_code, search_city
    >>> 
    >>> # Get postal code information
    >>> result = get_postal_code("94107", country_code="US")
    >>> print(f"City: {result['city']}, State: {result['state']}")
    >>> 
    >>> # Search for cities
    >>> cities = search_city("London", country_code="GB", limit=3)
    >>> for city in cities:
    >>>     print(f"{city['postal_code']}: {city['city']}")
    >>> 
    >>> # Find nearby postal codes
    >>> nearby = find_nearby(37.7749, -122.4194, radius_km=5)
    >>> for place in nearby:
    >>>     print(f"{place['city']} ({place['distance_km']} km away)")

All data is embedded in the package - no internet connection required.
Data sourced from GeoNames (https://www.geonames.org/).
"""

from .core import (
    get_postal_code,
    search_city,
    get_country_postal_codes,
    find_nearby,
    get_stats,
    get_countries,
    GeoNamesDatabase,
    PostalCodeRecord
)

__version__ = "1.0.0"
__author__ = "BD Geocode Team"
__email__ = ""
__license__ = "MIT"

__all__ = [
    'get_postal_code',
    'search_city', 
    'get_country_postal_codes',
    'find_nearby',
    'get_stats',
    'get_countries',
    'GeoNamesDatabase',
    'PostalCodeRecord'
]
'''
        
        with open(self.source_dir / "__init__.py", "w") as f:
            f.write(init_content)
        
        print("✓ Created __init__.py")
    
    def create_data_init_file(self):
        """Create __init__.py for data directory"""
        with open(self.data_dir / "__init__.py", "w") as f:
            f.write("# GeoNames embedded data files\n")
    
    def create_setup_py(self):
        """Create setup.py file"""
        print("\nCreating setup.py...")
        
        setup_content = '''from setuptools import setup, find_packages
import os

# Read README for long description
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

# Get package data files
def get_package_data():
    data_files = []
    for root, dirs, files in os.walk("zip_finder/data"):
        for file in files:
            if not file.endswith('.py'):
                rel_path = os.path.relpath(os.path.join(root, file), "zip_finder")
                data_files.append(rel_path.replace(os.sep, '/'))
    return data_files

setup(
    name="zip-finder",
    version="2.0.0",
    author="Karthikeyan Balasundaram",
    author_email="",
    description="Offline GeoNames postal code database for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/zip-finder",
    packages=find_packages(),
    package_data={
        'zip_finder': get_package_data(),
    },
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Scientific/Engineering :: GIS",
        "Topic :: Database",
    ],
    python_requires=">=3.7",
    install_requires=[],
    keywords="geonames postal codes zip codes offline database geocoding zip_finder",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/zip-finder/issues",
        "Source": "https://github.com/yourusername/zip-finder",
    },
)
'''
        
        with open(self.base_dir / "setup.py", "w") as f:
            f.write(setup_content)
        
        print("✓ Created setup.py")
    
    def create_pyproject_toml(self):
        """Create pyproject.toml file"""
        print("\nCreating pyproject.toml...")
        
        pyproject_content = '''[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "zip-finder"
readme = "README.md"
requires-python = ">=3.7"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
    "Topic :: Software Development :: Libraries :: Python Modules",
    "Topic :: Scientific/Engineering :: GIS",
]

[project.urls]
"Homepage" = "https://github.com/yourusername/zip-finder"
"Bug Tracker" = "https://github.com/yourusername/zip-finder/issues"
'''
        
        with open(self.base_dir / "pyproject.toml", "w") as f:
            f.write(pyproject_content)
        
        print("✓ Created pyproject.toml")
    
    def create_readme(self):
        """Create README.md file"""
        print("\nCreating README.md...")
        
        readme_content = '''# zip_finder

Complete offline GeoNames postal code / geocode database for Python.

## Features

- 🌍 **Complete coverage** - Postal codes for 200+ countries
- 📦 **Fully offline** - No internet connection required
- ⚡ **O(1) lookups** - Hash-indexed by country+zip and zip-only
- 🗺️ **Spatial search** - Geo-grid bucketed radius search (O(C + K·log K))
- 📊 **Multiple search methods** - By postal code, city, or coordinates
- 🔍 **Flexible matching** - Exact or partial (bisect prefix search)
- 🚀 **Zero dependencies** - Only Python standard library required
- 💾 **TB/ZB scale** - SQLite streaming mode for datasets exceeding RAM

## Installation

```bash
pip install zip-finder'''