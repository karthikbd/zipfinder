#!/usr/bin/env python3
"""
Advanced usage examples
"""
from bd_geocode_offline import get_stats, get_countries, search

def main():
    print("Advanced Usage Examples")
    print("=" * 50)
    
    # 1. Get statistics
    stats = get_stats()
    print(f"1. Database Statistics:")
    print(f"   Total records: {stats.get('total_records', 0):,}")
    print(f"   Countries: {stats.get('countries', 0)}")
    
    # 2. List countries
    countries = get_countries()
    print(f"\n2. Available Countries ({len(countries)}):")
    print(f"   Sample: {', '.join(countries[:10])}")
    
    # 3. Partial search
    print(f"\n3. Partial postal code search '100' in US:")
    results = search("100", country="US", limit=5)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['postal_code']}: {r['city']}, {r['state']}")

if __name__ == "__main__":
    main()