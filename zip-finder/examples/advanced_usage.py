#!/usr/bin/env python3
"""
Advanced usage examples
"""
from zip_finder import get_db_stats, list_countries, search_zip

def main():
    print("Advanced Usage Examples")
    print("=" * 50)
    
    # 1. Get database statistics
    stats = get_db_stats()
    print(f"1. Database Statistics:")
    print(f"   Total records: {stats.get('total_records', 0):,}")
    print(f"   Countries: {stats.get('countries', 0)}")
    
    # 2. List all available countries
    countries = list_countries()
    print(f"\n2. Available Countries ({len(countries)}):")
    print(f"   Sample: {', '.join(countries[:10])}")
    
    # 3. Partial zip/city search
    print(f"\n3. Partial postal code search '100' in US:")
    results = search_zip("100", country="US", limit=5)
    for i, r in enumerate(results, 1):
        print(f"   {i}. {r['postal_code']}: {r['city']}, {r['state']}")

if __name__ == "__main__":
    main()