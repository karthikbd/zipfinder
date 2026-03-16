"""
GeoNames data files for zip_finder package.
"""

DATA_FILES = [
    'geonames_data.jsonl.gz',
    'country_index.pkl.gz',
    'postal_index.pkl.gz',
    'metadata.json',
    'sample_data.jsonl.gz'
]

def list_data_files():
    """List all available data files"""
    return DATA_FILES
