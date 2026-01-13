"""
Core functionality tests
"""
import pytest
from bd_geocode_offline import get, search, get_stats, get_countries

def test_get():
    """Test basic get functionality"""
    result = get("94107", country="US")
    assert result is not None
    assert result['postal_code'] == "94107"
    assert result['country_code'] == "US"

def test_search():
    """Test search functionality"""
    results = search("London", country="GB", limit=3)
    assert isinstance(results, list)
    assert len(results) <= 3
    
    for r in results:
        assert "London" in r['city'] or "london" in r['city'].lower()
        assert r['country_code'] == "GB"

def test_get_stats():
    """Test statistics"""
    stats = get_stats()
    assert isinstance(stats, dict)
    assert 'total_records' in stats
    assert stats['total_records'] > 0

def test_get_countries():
    """Test countries list"""
    countries = get_countries()
    assert isinstance(countries, list)
    assert len(countries) > 0
    assert "US" in countries
    assert "GB" in countries