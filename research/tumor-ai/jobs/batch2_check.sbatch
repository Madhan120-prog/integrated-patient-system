#!/bin/bash
#SBATCH --job-name=batch2_check
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# D1 (no training): score the finished E3 fold 0 model on its own 284 TRAINING patients.
# About the same as on validation (~0.45) = it cannot even fit what it has seen: fix the model/training.
# Much higher (~0.8) = it memorises but does not generalise: fix with augmentation/regularisation.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --eval-only --on train --from full_e3_fold0 --name d1_trainfit_fold0 \
    --exp D1 --change "E3 fold 0 scored on its own training patients" --cutoffs 0.3 0.5
