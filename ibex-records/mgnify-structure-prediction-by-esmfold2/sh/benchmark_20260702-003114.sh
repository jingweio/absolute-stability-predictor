#!/bin/bash
#SBATCH --job-name=esmf2_bench
#SBATCH --gres=gpu:a100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=01:00:00
#SBATCH --output=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/benchmark_20260702-003114_%j.out
#SBATCH --error=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2/ibex-records/mgnify-structure-prediction-by-esmfold2/results/benchmark_20260702-003114_%j.err

set -euo pipefail
CONDA_BASE=/ibex/user/guoj0f/anaconda3
IBEXBR=/ibex/user/guoj0f/absolute-stability-predictor/mgnify-structure-prediction-by-esmfold2
export HF_HOME=/ibex/user/guoj0f/share/hf_cache

source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate mgnify-esm

nvidia-smi --query-gpu=name,memory.total --format=csv || true
python -c "import torch;print('torch',torch.__version__,'cuda',torch.cuda.is_available(),torch.cuda.get_device_name(0))"

MANIFEST=$IBEXBR/data/esmfold2_fast_wt_input/wt_manifest.csv
OUTDIR=$IBEXBR/data/esmfold2-fast-pred-structure
LOGDIR=$IBEXBR/ibex-records/mgnify-structure-prediction-by-esmfold2/results/benchmark_logs

echo "=== BENCHMARK: 200 WT, bfloat16, num_loops=3 num_sampling_steps=50 ==="
time python $IBEXBR/mgnify-structure-prediction/esmfold2_fast_predict.py \
    --manifest "$MANIFEST" --out-dir "$OUTDIR" --log-dir "$LOGDIR" \
    --shard-id 0 --num-shards 1 --limit 200 \
    --model biohub/ESMFold2-Fast --num-loops 3 --num-sampling-steps 50 \
    --dtype bfloat16 --seed 0 --hf-home "$HF_HOME"

echo "=== output footprint sample ==="
NFILES=$(find "$OUTDIR" -name '*.cif.gz' | wc -l)
BYTES=$(find "$OUTDIR" -name '*.cif.gz' -printf '%s\n' | awk '{s+=$1} END{print s}')
echo "files=$NFILES total_bytes=$BYTES avg_kb=$(awk "BEGIN{if($NFILES>0)printf \"%.1f\", $BYTES/1024/$NFILES}")"
echo "BENCHMARK DONE"
