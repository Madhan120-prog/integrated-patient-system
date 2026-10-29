#!/bin/bash
#SBATCH --job-name=full_e3
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%j.out
# E3: our U-Net, all patients, one fold per array task (0-4). Training scans are held in RAM (~30 GB).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold $SLURM_ARRAY_TASK_ID --base 32 --patch 48 160 160 --steps 50000 --val-every 5000 \
    --name full_e3_fold$SLURM_ARRAY_TASK_ID
