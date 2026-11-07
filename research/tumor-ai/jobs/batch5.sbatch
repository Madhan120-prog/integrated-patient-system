#!/bin/bash
#SBATCH --job-name=batch5
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-3
#SBATCH --output=logs/%x_task%a_%A.out
# Batch 5, fold 0, 2 seeds each. Compare with b3_long_fold0 + _seed7 (bigger block, 100,000 steps, mean 0.567).
# Slurm keeps its own copy of this file when you submit, so editing it later never changes queued runs.
RUNS=(
  "b5_vlong_fold0|B5 longer|bigger block, 200,000 steps|--steps 200000 --val-every 20000"
  "b5_vlong_seed7_fold0|B5 longer|bigger block, 200,000 steps, seed 7|--steps 200000 --val-every 20000 --seed 7"
  "b5_huge_long_fold0|B5 block+long|even bigger block 80x224x224, 100,000 steps|--patch 80 224 224 --steps 100000 --val-every 10000"
  "b5_huge_long_seed7_fold0|B5 block+long|even bigger block 80x224x224, 100,000 steps, seed 7|--patch 80 224 224 --steps 100000 --val-every 10000 --seed 7"
)
IFS='|' read -r NAME EXP CHANGE EXTRA <<< "${RUNS[$SLURM_ARRAY_TASK_ID]}"
echo "task $SLURM_ARRAY_TASK_ID: $NAME ($EXP) $CHANGE | $EXTRA"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --patch 64 192 192 \
    --name "$NAME" --exp "$EXP" --change "$CHANGE" $EXTRA
