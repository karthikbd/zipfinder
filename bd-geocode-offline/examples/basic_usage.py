#!/usr/bin/env python3
"""
Basic usage examples
"""
from bd_geocode_offline import get, search, find_nearby

def main():
    print("Basic Usage Examples")
    print("=" * 50)
    
    # 1. Get a postal code
    result = get("94107", country="US")
    print(f"1. Postal code 94107, US:")
    if result:
        print(f"   {result['city']}, {result['state']}")
        print(f"   Coordinates: {result['latitude']}, {result['longitude']}")
    
    # 2. Search
    print(f"\n2. Search for 'London' in GB:")
    results = search("London", country="GB", limit=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['postal_code']}: {r['city']}")
    
    # 3. Find nearby
    print(f"\n3. Near San Francisco (37.7749, -122.4194):")
    nearby = find_nearby(37.7749, -122.4194, radius_km=5, limit=3)
    for i, place in enumerate(nearby, 1):
        print(f"   {i}. {place['city']} ({place['distance_km']} km)")

if __name__ == "__main__":
    main()