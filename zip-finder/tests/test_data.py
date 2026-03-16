"""
Data validation tests
"""
import json
import gzip
from pathlib import Path

def test_data_files():
    """Verify data files exist and are valid"""
    data_dir = Path("zip_finder/data")
    
    # Check required files
    required = ['geonames_data.jsonl.gz', 'metadata.json']
    for file in required:
        assert (data_dir / file).exists(), f"Missing {file}"
    
    # Check JSONL format
    with gzip.open(data_dir / 'geonames_data.jsonl.gz', 'rt') as f:
        line = f.readline()
        record = json.loads(line)
        assert 'country_code' in record
        assert 'postal_code' in record
        assert 'city' in record
    
    # Check metadata
    with open(data_dir / 'metadata.json', 'r') as f:
        metadata = json.load(f)
        assert 'total_records' in metadata