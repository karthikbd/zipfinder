"""
Core functionality tests
"""
import pytest
from zip_finder import lookup_zip, search_zip, get_db_stats, list_countries

def test_lookup_zip():
    """Test lookup_zip returns the correct record"""
    result = lookup_zip("94107", country="US")
    assert result is not None
    assert result['postal_code'] == "94107"
    assert result['country_code'] == "US"

def test_search_zip():
    """Test search_zip prefix search"""
    results = search_zip("London", country="GB", limit=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    
    for r in results:
        assert "London" in r['city'] or "london" in r['city'].lower()
        assert r['country_code'] == "GB"

def test_get_db_stats():
    """Test get_db_stats returns valid statistics"""
    stats = get_db_stats()
    assert isinstance(stats, dict)
    assert 'total_records' in stats
    assert stats['total_records'] > 0

def test_list_countries():
    """Test list_countries returns all available country codes"""
    countries = list_countries()
    assert isinstance(countries, list)
    assert len(countries) > 0
    assert "US" in countries
    assert "GB" in countries