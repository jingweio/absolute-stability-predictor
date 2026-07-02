#!/usr/bin/env python3
"""Build the fold list for orphan-scaffold WT sequences + a downstream link manifest.

Context: 'orphan' scaffolds are PDB_name values that appear in mgnify_training_index.csv
ONLY via mutant rows (no name==PDB_name WT row), because the parent WT was filtered out of
the training index (train_name is empty in the full dataset CSV). Their WT SEQUENCE is still
present in the full dataset CSV (aa_seq). We fold those WT so the orphan MUTANTS — which ARE
in training — can be threaded onto their parent WT structure, matching the paper's
PDB_name -> WT-structure scheme.

IMPORTANT (preserve the authors' benchmark design): these WT are STRUCTURE-ONLY. They were
deliberately filtered from training/benchmark and carry NO dG label; we do NOT add them as
samples. Orphan mutants stay ddG-INELIGIBLE (no WT ΔG reference), consistent with the design.

Only READS existing data; only WRITES new files under --out-dir.
"""
import argparse
import csv
import hashlib
import os

csv.field_size_limit(1 << 24)


def bucket_of(_id: str) -> str:
    return hashlib.md5(_id.encode()).hexdigest()[:2]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full-csv", default="data/230515_K50dG_dmsv4_dmsv5_dmsv7_concat260429.csv")
    ap.add_argument("--index-csv", default="data/mgnify_training_index.csv")
    ap.add_argument("--orphan-list", default="data/esmfold2_fast_wt_input/orphan_pdb_names.txt")
    ap.add_argument("--out-dir", default="data/esmfold2_fast_orphan_wt_input")
    ap.add_argument("--struct-subdir", default="esmfold2-fast-pred-structure-orphan-wt",
                    help="dir (under data/) where the orphan WT structures will be written")
    args = ap.parse_args()
    os.makedirs(args.out_dir, exist_ok=True)

    orph = set(l.strip() for l in open(args.orphan_list) if l.strip())

    # 1) recover WT seq for each orphan scaffold from the full dataset CSV (name == orphan)
    wt = {}
    with open(args.full_csv) as fh:
        for row in csv.DictReader(fh):
            nm = row["name"]
            if nm in orph and nm not in wt:
                wt[nm] = row["aa_seq"]
    missing = sorted(orph - set(wt))

    man = os.path.join(args.out_dir, "orphan_wt_manifest.csv")
    fa = os.path.join(args.out_dir, "orphan_wt.fasta")
    with open(man, "w", newline="") as mf, open(fa, "w") as ff:
        w = csv.writer(mf)
        w.writerow(["id", "PDB_name", "split", "seq_len", "seq"])
        for _id in sorted(wt):
            seq = wt[_id]
            # split marker makes it explicit these are structure-only, not training samples
            w.writerow([_id, _id, "filtered_wt_structure_only", len(seq), seq])
            ff.write(f">{_id}\n{seq}\n")

    # 2) link: each orphan MUTANT row (in the training index) -> its parent WT structure path
    link = os.path.join(args.out_dir, "orphan_mutant_structure_links.csv")
    n_links = 0
    with open(args.index_csv) as fh, open(link, "w", newline="") as lf:
        w = csv.writer(lf)
        w.writerow(["mutant_name", "PDB_name", "split", "dG", "wt_structure_relpath", "ddg_eligible"])
        for row in csv.DictReader(fh):
            pdb = row["PDB_name"]
            if pdb in orph and row["name"] != pdb:  # an orphan mutant row
                relpath = f"data/{args.struct_subdir}/{bucket_of(pdb)}/{pdb}.cif.gz"
                w.writerow([row["name"], pdb, row["split"], row["dG"], relpath, "False"])
                n_links += 1

    print(f"orphan scaffolds        : {len(orph):,}")
    print(f"WT seq recovered        : {len(wt):,}")
    print(f"orphan WT missing seq   : {len(missing):,}")
    print(f"orphan mutant links     : {n_links:,}")
    print(f"wrote {man}")
    print(f"wrote {fa}")
    print(f"wrote {link}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
