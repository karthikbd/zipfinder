"""
Performance tests
"""
import time
from bd_geocode_offline import get, search

def test_get_performance():
    """Test get performance"""
    start = time.time()
    
    # Test 100 lookups
    for _ in range(100):
        get("94107", country="US")
    
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"

def test_search_performance():
    """Test search performance"""
    start = time.time()
    
    # Test 10 searches
    for _ in range(10):
        search("London", country="GB", limit=5)
    
    elapsed = time.time() - start
    assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"