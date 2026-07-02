#!/bin/bash
#SBATCH --job-name=esmf2_orphan
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=00:45:00
#SBATCH --array=0-7%8
#SBATCH --output=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/orphan_fold_logs/orphan_%A_%a.out
#SBATCH --error=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/orphan_fold_logs/orphan_%A_%a.err

# Supplementary run: fold the 4,623 orphan-scaffold WT sequences (WT filtered out of the
# training index; recovered from the full dataset CSV). STRUCTURE-ONLY — provides parent
# structures for the 6,391 orphan mutant rows (all in the TRAIN split). Kept in a SEPARATE
# output dir so it never mixes with the main 528,365 WT structures. Same env/weights/config.
set -euo pipefail
CONDA_BASE=/ibex/user/guoj0f/anaconda3
IBEXBR=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2
export HF_HOME=/ibex/user/guoj0f/share/hf_cache
NUM_SHARDS=8          # MUST match the --array size above

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate mgnify-esm

MANIFEST=$IBEXBR/data/esmfold2_fast_orphan_wt_input/orphan_wt_manifest.csv
OUTDIR=$IBEXBR/data/esmfold2-fast-pred-structure-orphan-wt      # SEPARATE from the main dir
LOGDIR=$IBEXBR/ibex-records/mgnify-structure-prediction-by-esmfold2/results/orphan_fold_logs
mkdir -p "$LOGDIR"

echo "orphan shard $SLURM_ARRAY_TASK_ID / $NUM_SHARDS on $(hostname)"
python $IBEXBR/mgnify-structure-prediction/esmfold2_fast_predict.py \
    --manifest "$MANIFEST" --out-dir "$OUTDIR" --log-dir "$LOGDIR" \
    --shard-id "$SLURM_ARRAY_TASK_ID" --num-shards "$NUM_SHARDS" \
    --model biohub/ESMFold2-Fast --num-loops 3 --num-sampling-steps 50 \
    --dtype float32 --seed 0 --hf-home "$HF_HOME"
