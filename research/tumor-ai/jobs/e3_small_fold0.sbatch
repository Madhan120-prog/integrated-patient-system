#!/bin/bash
#SBATCH --job-name=e3_small_fold0
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# E3-small: our 3D U-Net, base 32, fold 0 of the 50-patient split.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits.json \
    --fold 0 --base 32 --patch 48 160 160 --steps 20000 --val-every 1000 --name e3_small_fold0
