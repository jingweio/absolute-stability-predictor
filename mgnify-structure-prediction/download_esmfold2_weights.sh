#!/usr/bin/env bash
# Download ESMFold2-Fast + its ESMC-6B backbone into the shared HF cache.
# Weights are shared, large artifacts -> shared store (share/hf_cache), per ibex-usage skill §1d.
set -euo pipefail
export HF_HOME="${HF_HOME:-/home/guoj0f/share/hf_cache}"
mkdir -p "$HF_HOME"
echo "HF_HOME=$HF_HOME"
python3 - <<'PY'
import os
os.environ.setdefault("HF_HOME", "/home/guoj0f/share/hf_cache")
try:
    from huggingface_hub import snapshot_download
except ImportError:
    import subprocess, sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "huggingface_hub"])
    from huggingface_hub import snapshot_download
for repo in ["biohub/ESMFold2-Fast", "biohub/ESMC-6B"]:
    print(f"==> downloading {repo}", flush=True)
    p = snapshot_download(repo_id=repo)
    print(f"==> done {repo} -> {p}", flush=True)
PY
echo "ALL WEIGHTS DONE"
du -sh "$HF_HOME"/hub/* 2>/dev/null || true
