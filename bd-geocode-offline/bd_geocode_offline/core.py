"""
Core GeoNames database functionality
"""
import gzip
import json
import pickle
import pkgutil
import math
from typing import List, Dict, Optional, Tuple
from functools import lru_cache


class GeoNamesDatabase:
    """Singleton database with in-memory indexes"""
    
    _instance = None
    _data = None
    _country_index = None
    _postal_index = None
    _coordinate_index = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._data is None:
            self._load_data()
    
    def _load_data(self):
        """Load and index all data"""
        print("Loading GeoNames database...")
        
        # Try to load pre-built indexes first
        try:
            # Load country index
            country_data = pkgutil.get_data(__name__, 'data/country_index.pkl.gz')
            self._country_index = pickle.loads(gzip.decompress(country_data))
            
            # Load postal index
            postal_data = pkgutil.get_data(__name__, 'data/postal_index.pkl.gz')
            self._postal_index = pickle.loads(gzip.decompress(postal_data))
            
            print(f"✓ Loaded indexes: {len(self._country_index)} countries")
            
        except:
            # Fallback: Build indexes from JSONL
            self._build_indexes_from_jsonl()
        
        # Build coordinate index
        self._build_coordinate_index()
    
    def _build_indexes_from_jsonl(self):
        """Build indexes from JSONL data"""
        print("Building indexes from JSONL...")
        
        self._country_index = {}
        self._postal_index = {}
        self._data = []
        
        data_bytes = pkgutil.get_data(__name__, 'data/geonames_data.jsonl.gz')
        
        for line in gzip.decompress(data_bytes).decode('utf-8').splitlines():
            try:
                record = json.loads(line)
                self._data.append(record)
                
                # Country index
                country = record['country_code']
                if country not in self._country_index:
                    self._country_index[country] = []
                self._country_index[country].append(record)
                
                # Postal index
                key = f"{country}:{record['postal_code']}"
                self._postal_index[key] = record
                
            except:
                continue
        
        print(f"✓ Built indexes: {len(self._data):,} records, {len(self._country_index)} countries")
    
    def _build_coordinate_index(self):
        """Build coordinate index for spatial searches"""
        self._coordinate_index = []
        
        if self._data:
            # Use main data
            for record in self._data:
                self._add_to_coordinate_index(record)
        else:
            # Use country index
            for records in self._country_index.values():
                for record in records:
                    self._add_to_coordinate_index(record)
    
    def _add_to_coordinate_index(self, record):
        """Add valid coordinate to index"""
        try:
            lat = float(record['latitude'])
            lon = float(record['longitude'])
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                self._coordinate_index.append((lat, lon, record))
        except:
            pass
    
    def _haversine(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in km"""
        R = 6371.0
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))
    
    # ========== PUBLIC API ==========
    
    def get(self, postal_code: str, country: str = None) -> Optional[Dict]:
        """Get a single postal code"""
        if country:
            key = f"{country.upper()}:{postal_code}"
            return self._postal_index.get(key)
        else:
            # Fallback search
            if self._data:
                for record in self._data:
                    if record['postal_code'] == postal_code:
                        return record
            return None
    
    def search(self, query: str, country: str = None, limit: int = 10) -> List[Dict]:
        """Search by postal code or city name"""
        results = []
        query_lower = query.lower()
        
        if country:
            country = country.upper()
            if country in self._country_index:
                records = self._country_index[country]
            else:
                return []
        else:
            # Get all records
            if self._data:
                records = self._data
            else:
                records = []
                for rec_list in self._country_index.values():
                    records.extend(rec_list)
        
        for record in records:
            # Check postal code
            if query_lower in record['postal_code'].lower():
                results.append(record)
                if len(results) >= limit:
                    break
            
            # Check city name
            elif query_lower in record['city'].lower():
                results.append(record)
                if len(results) >= limit:
                    break
        
        return results[:limit]
    
    def find_nearby(self, latitude: float, longitude: float, 
                   radius_km: float = 10.0, limit: int = 10) -> List[Dict]:
        """Find nearby postal codes"""
        results = []
        
        for lat, lon, record in self._coordinate_index:
            distance = self._haversine(latitude, longitude, lat, lon)
            if distance <= radius_km:
                result = record.copy()
                result['distance_km'] = round(distance, 2)
                results.append((distance, result))
                if len(results) >= limit * 3:
                    break
        
        results.sort(key=lambda x: x[0])
        return [r[1] for r in results[:limit]]
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        # Try to load metadata
        try:
            metadata = pkgutil.get_data(__name__, 'data/metadata.json')
            return json.loads(metadata.decode('utf-8'))
        except:
            # Calculate stats
            total = len(self._data) if self._data else sum(len(v) for v in self._country_index.values())
            return {
                'total_records': total,
                'countries': len(self._country_index),
            }
    
    def get_countries(self) -> List[str]:
        """Get available country codes"""
        return sorted(self._country_index.keys())


# Singleton instance
_db_instance = None

def get_database():
    global _db_instance
    if _db_instance is None:
        _db_instance = GeoNamesDatabase()
    return _db_instance

@lru_cache(maxsize=1000)
def get(postal_code: str, country: str = None) -> Optional[Dict]:
    return get_database().get(postal_code, country)

def search(query: str, country: str = None, limit: int = 10) -> List[Dict]:
    return get_database().search(query, country, limit)

def find_nearby(latitude: float, longitude: float, 
               radius_km: float = 10.0, limit: int = 10) -> List[Dict]:
    return get_database().find_nearby(latitude, longitude, radius_km, limit)

def get_stats() -> Dict:
    return get_database().get_stats()

def get_countries() -> List[str]:
    return get_database().get_countries()