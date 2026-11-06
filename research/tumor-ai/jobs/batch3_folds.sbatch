#!/bin/bash
#SBATCH --job-name=batch3_folds
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --array=1-4
#SBATCH --output=logs/%x_fold%a_%A.out
# Batch 3: the bigger block (64x192x192, best in batch 1) on folds 1-4. Fold 0 already exists: e12_patch_big_fold0.
# Together they give a 5-fold result, compared with E3's 5 folds. Each run refuses to overwrite an existing folder.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold $SLURM_ARRAY_TASK_ID --base 32 --patch 64 192 192 --steps 50000 --val-every 5000 \
    --name b3_big_fold$SLURM_ARRAY_TASK_ID --exp "B3 big 5-fold" --change "bigger block 64x192x192"
