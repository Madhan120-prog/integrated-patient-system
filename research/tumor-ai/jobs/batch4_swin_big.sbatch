#!/bin/bash
#SBATCH --job-name=b4_swin_big
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --output=logs/%x_%j.out
# Batch 4: our two best single changes together, fold 0: Swin UNETR (e6_swin_fold0, 0.517, block 64x160x160)
# + the bigger block 64x192x192 (e12_patch_big_fold0, 0.545). Same settings as e6_swin_fold0 otherwise.
# Refuses to start if runs/b4_swin_big_fold0 already holds anything.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --steps 50000 --val-every 5000 --arch swin --patch 64 192 192 --lr 1e-4 \
    --name b4_swin_big_fold0 --exp "B4 swin+big" --change "Swin UNETR with the bigger block 64x192x192"
