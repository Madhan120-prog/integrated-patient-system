#!/bin/bash
#SBATCH --job-name=e3_small_eval
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=01:00:00
#SBATCH --output=logs/%x_%j.out
# Re-score the trained E3-small model with overlapping prediction + largest tumour piece. No training.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits.json \
    --fold 0 --name e3_small_fold0 --eval-only
