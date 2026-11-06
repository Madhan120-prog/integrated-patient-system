#!/bin/bash
#SBATCH --job-name=batch3
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --array=0-8
#SBATCH --output=logs/%x_task%a_%A.out
# Batch 3: fold 0, every idea run with 2 seeds (42 and 7), because one run moves about +-0.05 by chance.
# Baseline = the bigger block: e12_patch_big_fold0 (seed 42, 0.545) and task 0 below (seed 7).
# Slurm keeps its own copy of this file when you submit, so editing it later never changes queued runs.
RUNS=(
  "b3_big_seed7_fold0|B3 baseline|bigger block 64x192x192, seed 7|--seed 7"
  "b3_huge_fold0|B3 block|even bigger block 80x224x224|--patch 80 224 224"
  "b3_huge_seed7_fold0|B3 block|even bigger block 80x224x224, seed 7|--patch 80 224 224 --seed 7"
  "b3_long_fold0|B3 longer|100,000 steps instead of 50,000|--steps 100000 --val-every 10000"
  "b3_long_seed7_fold0|B3 longer|100,000 steps, seed 7|--steps 100000 --val-every 10000 --seed 7"
  "b3_fg50_fold0|B3 small|half the blocks centred on tumour (was a third)|--fg 0.5"
  "b3_fg50_seed7_fold0|B3 small|half the blocks on tumour, seed 7|--fg 0.5 --seed 7"
  "b3_tversky_fold0|B3 small|Tversky loss (misses cost more)|--loss tversky"
  "b3_tversky_seed7_fold0|B3 small|Tversky loss, seed 7|--loss tversky --seed 7"
)
IFS='|' read -r NAME EXP CHANGE EXTRA <<< "${RUNS[$SLURM_ARRAY_TASK_ID]}"
echo "task $SLURM_ARRAY_TASK_ID: $NAME ($EXP) $CHANGE | $EXTRA"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --patch 64 192 192 --steps 50000 --val-every 5000 \
    --name "$NAME" --exp "$EXP" --change "$CHANGE" $EXTRA
