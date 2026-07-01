#!/usr/bin/env bash
# Build the dedicated conda env `mgnify-esm` on Ibex for ESMFold2-Fast folding.
# One dedicated env per working-branch/task (ibex-usage skill §4). Runs ON Ibex.
set -euo pipefail
CONDA_BASE=/ibex/user/guoj0f/anaconda3
ENV=mgnify-esm
ESM_SRC=/ibex/user/guoj0f/share/esm-latest/esm

source "$CONDA_BASE/etc/profile.d/conda.sh"

if conda env list | grep -qE "/envs/${ENV}([[:space:]]|$)"; then
    echo "[env] $ENV already exists — reusing"
else
    echo "[env] creating $ENV (python 3.12)"
    conda create -y -n "$ENV" python=3.12
fi
conda activate "$ENV"
python -V

echo "[pip] installing esm (editable) + deps from $ESM_SRC"
pip install --upgrade pip
pip install -e "$ESM_SRC"

# The default torch wheel pulled by esm is cu130 (CUDA 13), but Ibex a100 nodes run
# an older driver (CUDA 12.8 / 12080) -> torch.cuda fails to init. Reinstall torch
# built for cu128 so CUDA initialises on the compute nodes.
echo "[pip] reinstalling torch for cu128 (Ibex a100 driver = CUDA 12.8)"
pip install --force-reinstall torch --index-url https://download.pytorch.org/whl/cu128

echo "[verify] imports"
python - <<'PY'
import torch
print("torch", torch.__version__, "cuda", torch.version.cuda, "avail", torch.cuda.is_available())
import transformers
print("transformers", transformers.__version__)
from transformers.models.esmfold2.modeling_esmfold2 import ESMFold2Model  # noqa
from esm.models.esmfold2 import ESMFold2InputBuilder, ProteinInput, StructurePredictionInput  # noqa
print("esmfold2 imports OK")
PY

echo "[compileall] warm .pyc to avoid Lustre/Weka cold-import races"
SP="$CONDA_BASE/envs/$ENV/lib/python3.12/site-packages"
python -m compileall -q "$SP/torch" "$SP/transformers" "$SP/esm" 2>/dev/null || true

echo "ENV SETUP DONE"
