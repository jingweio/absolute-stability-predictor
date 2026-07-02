#!/usr/bin/env python3
"""Verify every WT in the manifest has a non-empty predicted structure.

Final-acceptance check (task requirement): confirms each sample got a structure.
Writes a `redo_manifest.csv` (same schema as the input manifest) containing only
the still-missing WT ids, so a final sweep can re-fold exactly those.
Optionally aggregates per-shard metric TSVs to summarise the pLDDT distribution.
"""
import argparse
import csv
import glob
import os

csv.field_size_limit(1 << 24)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--redo-manifest", default=None)
    ap.add_argument("--metrics-glob", default=None, help="e.g. '<log-dir>/shard*_metrics.tsv'")
    args = ap.parse_args()

    rows = []
    with open(args.manifest, newline="") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    missing = []
    done = 0
    for row in rows:
        p = os.path.join(args.out_dir, f"{row['id']}.cif.gz")
        if os.path.exists(p) and os.path.getsize(p) > 0:
            done += 1
        else:
            missing.append(row)

    total = len(rows)
    print(f"manifest total : {total:,}")
    print(f"done           : {done:,}")
    print(f"MISSING        : {len(missing):,}")
    pct = 100.0 * done / total if total else 0.0
    print(f"coverage       : {pct:.4f}%")

    if missing and args.redo_manifest:
        with open(args.redo_manifest, "w", newline="") as mf:
            w = csv.DictWriter(mf, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(missing)
        print(f"wrote redo manifest ({len(missing):,}) -> {args.redo_manifest}")

    if args.metrics_glob:
        plddts = []
        for f in glob.glob(args.metrics_glob):
            with open(f) as fh:
                next(fh, None)
                for line in fh:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) >= 3:
                        try:
                            plddts.append(float(parts[2]))
                        except ValueError:
                            pass
        if plddts:
            plddts.sort()
            n = len(plddts)
            mean = sum(plddts) / n
            # ESMFold2 pLDDT is on a 0-1 scale (not 0-100).
            print(f"\npLDDT over {n:,} folded: mean={mean:.3f} "
                  f"min={plddts[0]:.3f} p10={plddts[n//10]:.3f} "
                  f"median={plddts[n//2]:.3f} max={plddts[-1]:.3f}")
            lo = sum(1 for x in plddts if x < 0.5)
            mid = sum(1 for x in plddts if 0.5 <= x < 0.7)
            hi = n - lo - mid
            print(f"  <0.5 (low):  {lo:,} ({100*lo/n:.1f}%)")
            print(f"  0.5-0.7:     {mid:,} ({100*mid/n:.1f}%)")
            print(f"  >=0.7 (high):{hi:,} ({100*hi/n:.1f}%)")

    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())
