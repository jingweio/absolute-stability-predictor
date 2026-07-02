#!/usr/bin/env python3
"""Compare two structures of the SAME sequence — consistency metrics on CA atoms.

Used to sanity-check ESMFold2-Fast predictions against the repo author's provided
MGnify example structures (no experimental ground truth exists). Reports:
  - CA-RMSD after optimal (Kabsch) superposition
  - TM-score on that superposition (a lower bound on the TM-align optimum; no rotation search)
  - CA-lDDT (superposition-free local distance difference test; most robust here)

Reads .pdb / .cif / .cif.gz via biotite. Assumes 1:1 residue correspondence (same sequence).
"""
import argparse
import gzip

import numpy as np
import biotite.structure as struc
from biotite.structure.io.pdb import PDBFile
from biotite.structure.io.pdbx import CIFFile, get_structure


def load_ca(path: str) -> struc.AtomArray:
    if path.endswith(".cif.gz") or path.endswith(".cif"):
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rt") as fh:
            arr = get_structure(CIFFile.read(fh), model=1)
    else:
        arr = PDBFile.read(path).get_structure(model=1)
    arr = arr[struc.filter_amino_acids(arr)]
    # first chain only
    first = arr.chain_id[0]
    arr = arr[arr.chain_id == first]
    ca = arr[arr.atom_name == "CA"]
    # order by residue id
    order = np.argsort(ca.res_id)
    return ca[order]


def tm_score(ref_ca: np.ndarray, fit_ca: np.ndarray) -> float:
    L = len(ref_ca)
    d0 = max(0.5, 1.24 * (L - 15) ** (1.0 / 3.0) - 1.8) if L > 21 else 0.5
    d = np.linalg.norm(ref_ca - fit_ca, axis=1)
    return float(np.mean(1.0 / (1.0 + (d / d0) ** 2)))


def ca_lddt(ref: np.ndarray, pred: np.ndarray, r0: float = 15.0,
            thresholds=(0.5, 1.0, 2.0, 4.0)) -> float:
    n = len(ref)
    dref = np.linalg.norm(ref[:, None, :] - ref[None, :, :], axis=-1)
    dpred = np.linalg.norm(pred[:, None, :] - pred[None, :, :], axis=-1)
    mask = (dref < r0) & ~np.eye(n, dtype=bool)
    diff = np.abs(dref - dpred)[mask]
    if diff.size == 0:
        return float("nan")
    return float(np.mean([(diff < t).mean() for t in thresholds]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True, help="author/reference structure (.pdb/.cif/.cif.gz)")
    ap.add_argument("--pred", required=True, help="our ESMFold2-Fast structure (.cif.gz)")
    ap.add_argument("--label", default="")
    args = ap.parse_args()

    ref = load_ca(args.ref)
    pred = load_ca(args.pred)
    if len(ref) != len(pred):
        print(f"[{args.label}] WARNING length mismatch ref={len(ref)} pred={len(pred)} "
              f"→ truncating to min for comparison")
        m = min(len(ref), len(pred))
        ref, pred = ref[:m], pred[:m]

    fitted, _ = struc.superimpose(ref, pred)
    rmsd = float(struc.rmsd(ref, fitted))
    tm = tm_score(ref.coord, fitted.coord)
    lddt = ca_lddt(ref.coord, pred.coord)

    print(f"[{args.label}] L={len(ref)}  CA-RMSD={rmsd:.2f} Å  "
          f"TM-score(Kabsch,≥lower-bound)={tm:.3f}  CA-lDDT={lddt:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
