#!/usr/bin/env python3
"""Batch WT structure prediction for MGnify Stability using ESMFold2-Fast.

Single-sequence (no MSA) folding with the fast checkpoint ``biohub/ESMFold2-Fast``.
Designed for SLURM array parallelism: each array task processes one contiguous
shard of the WT manifest and is fully resumable (existing outputs are skipped).

Outputs, one gzipped mmCIF per WT, bucketed into 256 subdirs (md5[:2]) so no
single directory holds ~half a million files:
    <out_dir>/<bucket>/<id>.cif.gz
A per-shard TSV records id, seq_len, mean pLDDT, pTM and wall-time.

This script only WRITES new files under --out-dir / --log-dir; it never modifies
any existing repo file or dataset.
"""
import argparse
import csv
import gzip
import hashlib
import os
import sys
import time

csv.field_size_limit(1 << 24)


def bucket_of(_id: str) -> str:
    return hashlib.md5(_id.encode()).hexdigest()[:2]


def out_path(out_dir: str, _id: str) -> str:
    return os.path.join(out_dir, bucket_of(_id), f"{_id}.cif.gz")


def load_shard(manifest: str, shard_id: int, num_shards: int, limit: int | None):
    rows = []
    with open(manifest, newline="") as fh:
        for row in csv.DictReader(fh):
            rows.append((row["id"], row["seq"], int(row["seq_len"])))
    rows.sort(key=lambda r: r[0])  # deterministic order across runs
    shard = [r for i, r in enumerate(rows) if i % num_shards == shard_id]
    if limit is not None:
        shard = shard[:limit]
    return shard, len(rows)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--shard-id", type=int, default=0)
    ap.add_argument("--num-shards", type=int, default=1)
    ap.add_argument("--limit", type=int, default=None, help="cap #structures (benchmark)")
    ap.add_argument("--model", default="biohub/ESMFold2-Fast")
    ap.add_argument("--num-loops", type=int, default=3)
    ap.add_argument("--num-sampling-steps", type=int, default=50)
    ap.add_argument("--num-diffusion-samples", type=int, default=1)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--dtype", choices=["float32", "bfloat16", "float16"], default="bfloat16")
    ap.add_argument("--hf-home", default=os.environ.get("HF_HOME", "/ibex/user/guoj0f/share/hf_cache"))
    args = ap.parse_args()

    os.environ["HF_HOME"] = args.hf_home
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # weights pre-staged; don't hit network on compute node

    import torch
    from esm.models.esmfold2 import (
        ESMFold2InputBuilder,
        ProteinInput,
        StructurePredictionInput,
    )
    from transformers.models.esmfold2.modeling_esmfold2 import ESMFold2Model

    dtype = {"float32": torch.float32, "bfloat16": torch.bfloat16, "float16": torch.float16}[args.dtype]

    shard, total = load_shard(args.manifest, args.shard_id, args.num_shards, args.limit)
    os.makedirs(args.log_dir, exist_ok=True)
    for b in range(256):
        os.makedirs(os.path.join(args.out_dir, f"{b:02x}"), exist_ok=True)

    todo = [r for r in shard if not (os.path.exists(out_path(args.out_dir, r[0]))
                                     and os.path.getsize(out_path(args.out_dir, r[0])) > 0)]
    print(f"[shard {args.shard_id}/{args.num_shards}] total={total:,} "
          f"shard={len(shard):,} todo={len(todo):,} (skipping {len(shard)-len(todo):,} done)",
          flush=True)
    if not todo:
        print("nothing to do — shard already complete", flush=True)
        return 0

    print(f"loading {args.model} (dtype={args.dtype}) ...", flush=True)
    t0 = time.time()
    model = ESMFold2Model.from_pretrained(args.model, torch_dtype=dtype).cuda().eval()
    builder = ESMFold2InputBuilder()
    print(f"model loaded in {time.time()-t0:.1f}s; GPU mem {torch.cuda.max_memory_allocated()/1e9:.1f} GB",
          flush=True)

    tsv_path = os.path.join(args.log_dir, f"shard{args.shard_id:04d}_metrics.tsv")
    fail_path = os.path.join(args.log_dir, f"shard{args.shard_id:04d}_failures.tsv")
    tsv = open(tsv_path, "a")
    fails = open(fail_path, "a")
    if os.path.getsize(tsv_path) == 0:
        tsv.write("id\tseq_len\tmean_plddt\tptm\tsec\n")

    n_ok = n_fail = 0
    t_start = time.time()
    for k, (_id, seq, slen) in enumerate(todo):
        op = out_path(args.out_dir, _id)
        try:
            t1 = time.time()
            spi = StructurePredictionInput(sequences=[ProteinInput(id="A", sequence=seq)])
            res = builder.fold(
                model, spi,
                num_loops=args.num_loops,
                num_sampling_steps=args.num_sampling_steps,
                num_diffusion_samples=args.num_diffusion_samples,
                seed=args.seed,
                complex_id=_id,
            )
            cif = res.complex.to_mmcif()
            tmp = op + ".tmp"
            with gzip.open(tmp, "wt") as f:
                f.write(cif)
            os.replace(tmp, op)  # atomic: partial files never counted as done
            dt = time.time() - t1
            mplddt = float(res.plddt.mean())
            ptm = float(getattr(res, "ptm", float("nan")))
            tsv.write(f"{_id}\t{slen}\t{mplddt:.2f}\t{ptm:.4f}\t{dt:.2f}\n")
            n_ok += 1
        except Exception as e:  # noqa: BLE001 — keep the batch going, log the offender
            fails.write(f"{_id}\t{slen}\t{type(e).__name__}: {str(e)[:200]}\n")
            fails.flush()
            n_fail += 1
        if (k + 1) % 25 == 0 or k + 1 == len(todo):
            el = time.time() - t_start
            rate = (k + 1) / el
            tsv.flush()
            print(f"  {k+1:,}/{len(todo):,} ok={n_ok} fail={n_fail} "
                  f"{rate:.2f} str/s ({1/rate:.1f}s/str) eta={ (len(todo)-k-1)/rate/60:.1f} min",
                  flush=True)

    tsv.close()
    fails.close()
    print(f"[shard {args.shard_id}] DONE ok={n_ok} fail={n_fail} "
          f"elapsed={ (time.time()-t_start)/60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
