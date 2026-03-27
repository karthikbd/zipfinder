#!/usr/bin/env python3
"""
Basic usage examples
"""
from zip_finder import lookup_zip, lookup_all_zips, search_zip, find_nearby_zips

def main():
    print("ZipFinder — Basic Usage Examples")
    print("=" * 50)

    # 1. Exact lookup WITH country  → O(1)
    result = lookup_zip("94107", country="US")
    print("1. lookup_zip('94107', country='US')  [O(1)]:")
    if result:
        print(f"   {result['city']}, {result['state']}")
        print(f"   Coordinates: {result['latitude']}, {result['longitude']}")

    # 2. Exact lookup WITHOUT country → O(1)  (returns first match found)
    result2 = lookup_zip("94107")
    print(f"\n2. lookup_zip('94107')  [O(1), no country — returns first match]:")
    print(f"   {result2['city']}, {result2['country_code']}" if result2 else "   Not found")

    # 3. Get ALL matches across countries     → O(1)
    all_matches = lookup_all_zips("94107")
    print(f"\n3. lookup_all_zips('94107')  [O(1)] — {len(all_matches)} countr(ies):")
    for r in all_matches:
        print(f"   {r['country_code']}: {r['city']}")

    # 4. Prefix search  → O(log N + K)
    print("\n4. search_zip('Lon', country='GB', limit=3)  [O(log N + K)]:")
    results = search_zip("Lon", country="GB", limit=3)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['postal_code']}: {r['city']}")

    # 5. Spatial radius search  → O(C + K·log K)
    print("\n5. find_nearby_zips(37.7749, -122.4194, radius_km=5)  [O(C+K·log K)]:")
    nearby = find_nearby_zips(37.7749, -122.4194, radius_km=5, limit=3)
    for i, place in enumerate(nearby, 1):
        print(f"   {i}. {place['city']} ({place['distance_km']} km)")

if __name__ == "__main__":
    main()