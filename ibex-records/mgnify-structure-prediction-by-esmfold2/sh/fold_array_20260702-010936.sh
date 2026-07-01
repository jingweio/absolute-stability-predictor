#!/bin/bash
#SBATCH --job-name=esmf2_fold
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:15:00
#SBATCH --array=0-199%20
#SBATCH --output=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/fold_logs/fold_%A_%a.out
#SBATCH --error=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/fold_logs/fold_%A_%a.err

# Full WT structure prediction — ESMFold2-Fast, fp32, single-sequence.
# 528,365 WT split into NUM_SHARDS contiguous shards (one array task each).
# Fully resumable: existing outputs are skipped, so a timed-out/re-run shard continues.
set -euo pipefail
CONDA_BASE=/ibex/user/guoj0f/anaconda3
IBEXBR=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2
export HF_HOME=/ibex/user/guoj0f/share/hf_cache
NUM_SHARDS=200          # MUST match the --array size above

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate mgnify-esm

MANIFEST=$IBEXBR/data/esmfold2_fast_wt_input/wt_manifest.csv
OUTDIR=$IBEXBR/data/esmfold2-fast-pred-structure
LOGDIR=$IBEXBR/ibex-records/mgnify-structure-prediction-by-esmfold2/results/fold_logs
mkdir -p "$LOGDIR"

echo "shard $SLURM_ARRAY_TASK_ID / $NUM_SHARDS on $(hostname)"
python $IBEXBR/mgnify-structure-prediction/esmfold2_fast_predict.py \
    --manifest "$MANIFEST" --out-dir "$OUTDIR" --log-dir "$LOGDIR" \
    --shard-id "$SLURM_ARRAY_TASK_ID" --num-shards "$NUM_SHARDS" \
    --model biohub/ESMFold2-Fast --num-loops 3 --num-sampling-steps 50 \
    --dtype float32 --seed 0 --hf-home "$HF_HOME"
