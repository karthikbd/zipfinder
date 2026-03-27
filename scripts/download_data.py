#!/usr/bin/env python3
"""
Optional: Download latest GeoNames data
"""
import requests
import zipfile
import json
import gzip
from pathlib import Path

def download_geonames():
    """Download and update GeoNames data"""
    print("This is optional. Your package already contains data.")
    print("To update data, visit: https://download.geonames.org/export/zip/")
    
if __name__ == "__main__":
    download_geonames()