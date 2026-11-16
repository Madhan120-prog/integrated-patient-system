#!/bin/bash
#SBATCH --job-name=final_test
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# THE ONE FINAL TEST (60 locked patients), with the recipe fixed on validation BEFORE looking (batch 6, b6_avg_v1, 0.659):
#   0.25 x our U-Net (5 folds: b3_long_fold0, b5_long_fold1-4, centre-weighted)
#   + 0.75 x nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep, 5 folds each, saved test probabilities),
#   cut-off 0.3, most-confident piece.
# Also prints our U-Net alone and nnU-Net alone at the same setting. Writes a NEW file; earlier test files stay.
# Run it once. Whatever it says is the result.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
for t in resencL 1000ep; do [ -n "$(ls ../data/full/prob_nnunet_$t/test/*.npz 2>/dev/null)" ] || { echo "missing prob_nnunet_$t/test"; exit 1; }; done
../.venv/bin/python -u evaluate.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --ours b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4 --gauss --cutoff 0.3 --piece confident \
    --nnunet-prob ../data/full/prob_nnunet_resencL/test ../data/full/prob_nnunet_1000ep/test --weight 0.25 \
    --out ../results/test_scores_final.csv
