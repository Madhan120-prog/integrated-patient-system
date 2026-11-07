#!/bin/bash
#SBATCH --job-name=batch5_folds
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --array=1-4
#SBATCH --output=logs/%x_fold%a_%A.out
# Batch 5: our best recipe so far, bigger block 64x192x192 + 100,000 steps, on folds 1-4.
# Fold 0 already exists with these exact settings: b3_long_fold0. Each run refuses to overwrite an existing folder.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold $SLURM_ARRAY_TASK_ID --base 32 --patch 64 192 192 --steps 100000 --val-every 10000 \
    --name b5_long_fold$SLURM_ARRAY_TASK_ID --exp "B5 long 5-fold" --change "bigger block 64x192x192 + 100,000 steps"
