"""
zip_finder.utils — shared helper functions
"""
from typing import Dict, List
import math

def format_location(record: Dict) -> str:
    """Format location as string"""
    if not record:
        return "Not found"
    parts = []
    if record.get('city'):
        parts.append(record['city'])
    if record.get('state'):
        parts.append(record['state'])
    if record.get('country_code'):
        parts.append(record['country_code'])
    return ", ".join(parts)

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between coordinates in km"""
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))