#!/bin/bash
#SBATCH --job-name=e10_unet
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%A.out
# E10, the "after" number: our U-Net, the b5_long recipe (64x192x192 block, 100,000 steps; 0.582 over 5 folds),
# trained on Lung1 + new data (splits_multi.json). Validation = the same Lung1 patients, so it compares 1:1 with b5_long.
# More memory than b5 (128G): every training scan is held in memory and the thin-slice scans are big.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
K=$SLURM_ARRAY_TASK_ID
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset002_LungMulti --splits ../data/full/splits_multi.json \
    --fold $K --base 32 --patch 64 192 192 --steps 100000 --val-every 10000 \
    --name e10_unet_fold$K --exp "E10 more data" --change "b5_long recipe + Radiogenomics B + MSD Lung in training"
