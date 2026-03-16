#!/usr/bin/env python
"""
Step 3: Re-encode libpostal's text expansion dictionaries as DAWG.
Requires: pip install dawg2
Reduces address_expansions/ by ~50% vs double-array trie format.

NOTE: This step is OPTIONAL. If you skip it, the double-array tries
are used as-is (they still compress well under zstd in step 4).
"""
import pathlib, argparse, shutil

try:
    import dawg
except ImportError:
    print("dawg2 not installed — skipping DAWG re-encoding.")
    print("Run: pip install dawg2")
    raise SystemExit(0)

ap = argparse.ArgumentParser()
ap.add_argument("--datadir", required=True)
args = ap.parse_args()

data_dir = pathlib.Path(args.datadir)
exp_dir  = data_dir / "address_expansions"

if not exp_dir.exists():
    print(f"No address_expansions dir found at {exp_dir}, skipping.")
    raise SystemExit(0)

for txt_file in exp_dir.glob("*.txt"):
    print(f"  Building DAWG for {txt_file.name} …")
    phrases = [l.strip() for l in txt_file.read_text().splitlines() if l.strip()]
    d = dawg.DAWG(sorted(phrases))
    out = txt_file.with_suffix(".dawg")
    d.save(str(out))
    orig_kb = txt_file.stat().st_size / 1024
    new_kb  = out.stat().st_size / 1024
    print(f"    {orig_kb:.0f} KB → {new_kb:.0f} KB")

print("DAWG encoding complete.")
