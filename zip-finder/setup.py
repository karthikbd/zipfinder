from setuptools import setup, find_packages
import os

def get_package_data():
    data_files = []
    for root, dirs, files in os.walk("zip_finder/data"):
        for file in files:
            rel_path = os.path.relpath(os.path.join(root, file), "zip_finder")
            data_files.append(rel_path.replace(os.sep, '/'))
    return data_files

setup(
    name="zipfinder",
    version="2.0.0",
    packages=find_packages(exclude=[]),
    package_data={"zip_finder": get_package_data()},
    include_package_data=True,
)