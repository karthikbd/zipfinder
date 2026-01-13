#!/usr/bin/env python3
"""
Build the package
"""
import subprocess
import sys

def build():
    """Build the package"""
    print("Building bd-geocode-offline...")
    subprocess.run([sys.executable, "-m", "build"])
    print("✓ Build complete")
    print("\nTo upload to PyPI:")
    print("python -m twine upload dist/*")

if __name__ == "__main__":
    build()