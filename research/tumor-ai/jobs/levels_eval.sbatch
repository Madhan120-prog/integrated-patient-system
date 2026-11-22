#!/bin/bash
#SBATCH --job-name=levels_eval
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# XAI levels (paper, Section V): four-level explanations on
#   1. the fold-0 validation patients, with the recipe's fold-0 models (fair: never trained on them)
#   2. the 60 locked test patients, with the final 5-fold recipe (test already spent: describing only, no choices)
# Code runs from the git clone (~/ips: prototype/levels.py, levels_eval.py); data, runs and results from ~/tumor-ai.
# Writes results/levels_eval_fold0.csv and results/levels_eval_test.csv; refuses to overwrite either.
module load python/3.12.9/gcc.8.5.0
set -e
T=~/tumor-ai
cd ~/ips/research/tumor-ai/prototype
COMMON="--data $T/data/full/nnunet/Dataset001_LungGTV --splits $T/data/full/splits.json --runs $T/model/runs --cut 0.3"
P=$T/data/full
echo "=== fold 0 validation"
$T/.venv/bin/python -u levels_eval.py --set fold0 $COMMON --ours b3_long_fold0 \
    --nnunet-prob $P/prob_nnunet_resencL/val_fold0 $P/prob_nnunet_1000ep/val_fold0 \
    --model-text "25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep), fold 0" \
    --out $T/results/levels_eval_fold0.csv
echo "=== 60 locked test patients"
$T/.venv/bin/python -u levels_eval.py --set test $COMMON \
    --ours b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4 \
    --nnunet-prob $P/prob_nnunet_resencL/test $P/prob_nnunet_1000ep/test \
    --model-text "25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep), 5 folds" \
    --out $T/results/levels_eval_test.csv
