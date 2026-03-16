#!/usr/bin/env python
"""
Step 2 of the build pipeline.
Converts all float64 weight .bin files to int8 + per-row float32 scale.
Typically reduces perceptron files from ~600 MB to ~80 MB.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))
from address_finder._quantize import quantize_directory
import argparse

ap = argparse.ArgumentParser()
ap.add_argument("--src", required=True,
                help="Raw libpostal data dir, e.g. /tmp/postal_raw")
ap.add_argument("--dst", required=True,
                help="Output dir, e.g. address_finder/_data_raw")
args = ap.parse_args()
quantize_directory(args.src, args.dst)
