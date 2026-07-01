#!/usr/bin/env python3
"""Build the WT-only fold list for MGnify Stability structure prediction (ESMFold2-Fast).

WT definition: rows of ``mgnify_training_index.csv`` whose ``name == PDB_name``.
Each such row is a wild-type / parent scaffold; point mutants and indels reference
their parent via ``PDB_name`` and are NOT folded (per task decision: WT only).

Outputs (written next to the sequence data, untracked / synced to Ibex):
  <out_dir>/wt_manifest.csv   columns: id,PDB_name,split,seq_len,seq
  <out_dir>/wt.fasta          one record per WT ( >id ) — id == name == PDB_name
  <out_dir>/orphan_pdb_names.txt  PDB_names referenced only by mutants (no WT row)

This script only READS the existing dataset and WRITES new files; it never
modifies any existing repo file.
"""
import argparse
import csv
import os
import sys

csv.field_size_limit(1 << 24)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--index-csv",
        default="data/mgnify_training_index.csv",
        help="Path to mgnify_training_index.csv",
    )
    ap.add_argument(
        "--out-dir",
        default="data/esmfold2_fast_wt_input",
        help="Directory to write wt.fasta / wt_manifest.csv",
    )
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    manifest_path = os.path.join(args.out_dir, "wt_manifest.csv")
    fasta_path = os.path.join(args.out_dir, "wt.fasta")
    orphan_path = os.path.join(args.out_dir, "orphan_pdb_names.txt")

    all_pdb = set()
    wt = {}  # id -> (PDB_name, split, seq)
    n = 0
    with open(args.index_csv, newline="") as fh:
        r = csv.DictReader(fh)
        for row in r:
            n += 1
            name, pdb, seq, split = (
                row["name"],
                row["PDB_name"],
                row["seq"],
                row["split"],
            )
            all_pdb.add(pdb)
            if name == pdb:
                if name in wt:
                    print(f"WARNING: duplicate WT id {name}", file=sys.stderr)
                wt[name] = (pdb, split, seq)

    orphans = sorted(all_pdb - set(wt.keys()))

    with open(manifest_path, "w", newline="") as mf, open(fasta_path, "w") as ff:
        w = csv.writer(mf)
        w.writerow(["id", "PDB_name", "split", "seq_len", "seq"])
        for _id in sorted(wt.keys()):
            pdb, split, seq = wt[_id]
            w.writerow([_id, pdb, split, len(seq), seq])
            ff.write(f">{_id}\n{seq}\n")

    with open(orphan_path, "w") as of:
        of.write("\n".join(orphans) + ("\n" if orphans else ""))

    print(f"total rows read           : {n:,}")
    print(f"unique PDB_name           : {len(all_pdb):,}")
    print(f"WT folded (name==PDB_name): {len(wt):,}")
    print(f"orphan PDB_names (skipped): {len(orphans):,}")
    print(f"wrote manifest            : {manifest_path}")
    print(f"wrote fasta               : {fasta_path}")
    print(f"wrote orphan list         : {orphan_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
