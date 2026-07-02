#!/bin/bash
#SBATCH --job-name=esmf2_val
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:20:00
#SBATCH --output=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/val_fold_%j.out
#SBATCH --error=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/val_fold_%j.err

# Validation: fold the 2 author-provided MGnify example sequences with ESMFold2-Fast
# (same config as the main run), then compare to the author's structures (examples/mgnify_*.pdb).
set -euo pipefail
CONDA_BASE=/ibex/user/guoj0f/anaconda3
IBEXBR=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2
export HF_HOME=/ibex/user/guoj0f/share/hf_cache
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate mgnify-esm

MANIFEST=$IBEXBR/data/esmfold2_fast_validation_input/val_manifest.csv
OUTDIR=$IBEXBR/data/esmfold2-fast-pred-structure-validation
LOGDIR=$IBEXBR/ibex-records/mgnify-structure-prediction-by-esmfold2/results/val_fold_logs
mkdir -p "$LOGDIR"

echo "=== fold 2 validation cases (ESMFold2-Fast, fp32, loops=3 steps=50) ==="
python $IBEXBR/mgnify-structure-prediction/esmfold2_fast_predict.py \
    --manifest "$MANIFEST" --out-dir "$OUTDIR" --log-dir "$LOGDIR" \
    --shard-id 0 --num-shards 1 \
    --model biohub/ESMFold2-Fast --num-loops 3 --num-sampling-steps 50 \
    --dtype float32 --seed 0 --hf-home "$HF_HOME"

echo "=== compare vs author structures ==="
for id in mgnify_1A0N mgnify_1A32; do
    python $IBEXBR/mgnify-structure-prediction/compare_structures.py \
        --ref $IBEXBR/examples/${id}.pdb \
        --pred $OUTDIR/${id}.cif.gz \
        --label "$id"
done
echo "VALIDATION DONE"
