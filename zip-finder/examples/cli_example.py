#!/usr/bin/env python3
"""
CLI example
"""
import sys
from zip_finder import lookup_zip, search_zip

def main():
    if len(sys.argv) < 2:
        print("Usage: python cli_example.py <postal_code> [country]")
        print("       python cli_example.py search <query> [country]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "search":
        query = sys.argv[2] if len(sys.argv) > 2 else ""
        country = sys.argv[3] if len(sys.argv) > 3 else None
        results = search_zip(query, country=country, limit=5)
        print(f"Found {len(results)} results:")
        for r in results:
            print(f"  {r['postal_code']}: {r['city']}, {r['state']}")
    
    else:
        postal_code = command
        country = sys.argv[2] if len(sys.argv) > 2 else None
        result = lookup_zip(postal_code, country=country)
        if result:
            print(f"{result['city']}, {result['state']}, {result['country_code']}")
            print(f"Coordinates: {result['latitude']}, {result['longitude']}")
        else:
            print("Not found")

if __name__ == "__main__":
    main()