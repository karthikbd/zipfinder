from setuptools import setup, find_packages
import os

def get_package_data():
    data_files = []
    for root, dirs, files in os.walk("bd_geocode_offline/data"):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), "bd_geocode_offline")
            data_files.append(rel_path.replace(os.sep, '/'))
    return data_files

setup(
    name="bd-geocode-offline",
    version="1.0.0",
    packages=find_packages(),
    package_data={'bd_geocode_offline': get_package_data()},
    include_package_data=True,
)