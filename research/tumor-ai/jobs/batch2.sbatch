#!/bin/bash
#SBATCH --job-name=batch2
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_task%a_%A.out
# Batch 2: fold 0, compared with E3 fold 0 (val Dice 0.450). Same patients and 50,000 steps as E3.
# Slurm keeps its own copy of this file when you submit, so editing it later never changes queued runs.
# Each run writes runs/<name>/ and refuses to start if that folder already holds anything.
RUNS=(
  "e3_seed7_fold0|E3 repeat|E3 again with another seed (shows how much a score moves by chance)|--seed 7"
  "e4g_sgd_fold0|E4g|nnU-Net optimizer (SGD, momentum 0.99, lr 0.01)|--opt sgd --lr 0.01"
  "e4h_body_fold0|E4h|training blocks only from the box around the body|--crop-body"
  "e4_combo_fold0|E4 combo|brightness scaling + deep supervision + more augmentation + bigger block + body box|--norm zscore --deep-sup --aug more --patch 64 192 192 --crop-body"
  "e4_combo_sgd_fold0|E4 combo|combo above + nnU-Net optimizer|--norm zscore --deep-sup --aug more --patch 64 192 192 --crop-body --opt sgd --lr 0.01"
)
IFS='|' read -r NAME EXP CHANGE EXTRA <<< "${RUNS[$SLURM_ARRAY_TASK_ID]}"
echo "task $SLURM_ARRAY_TASK_ID: $NAME ($EXP) $CHANGE | $EXTRA"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --patch 48 160 160 --steps 50000 --val-every 5000 \
    --name "$NAME" --exp "$EXP" --change "$CHANGE" $EXTRA
