#!/bin/bash
#SBATCH --job-name=batch1_predict
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%A.out
# Batch 1, prediction-only (no training): E4a tumour cut-off and E4f centre-weighted blocks,
# tried on the finished E3 models, on each fold's own validation patients (never the test patients).
# The "plain_0.5" row repeats E3's own setting, so it must match E3's val Dice: a built-in check.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --eval-only --from full_e3_fold$SLURM_ARRAY_TASK_ID --name e4af_predict_fold$SLURM_ARRAY_TASK_ID \
    --exp E4a/E4f --change "cut-off (number) and centre-weighted blocks (gauss)" --cutoffs 0.2 0.3 0.4 0.5 --gauss
