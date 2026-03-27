"""
Performance tests
"""
import time
from zip_finder import lookup_zip, search_zip

def test_lookup_zip_performance():
    """Test lookup_zip O(1) lookup speed"""
    start = time.time()
    
    # Test 100 lookups
    for _ in range(100):
        lookup_zip("94107", country="US")
    
    elapsed = time.time() - start
    assert elapsed < 1.0, f"Too slow: {elapsed:.2f}s"

def test_search_zip_performance():
    """Test search_zip O(log N + K) speed"""
    start = time.time()
    
    # Test 10 searches
    for _ in range(10):
        search_zip("London", country="GB", limit=5)
    
    elapsed = time.time() - start
    assert elapsed < 2.0, f"Too slow: {elapsed:.2f}s"