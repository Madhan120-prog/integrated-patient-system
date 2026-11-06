#!/bin/bash
#SBATCH --job-name=batch3_test
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# Final test of the bigger-block U-Net (5 folds averaged) with the prediction setting chosen on VALIDATION
# (best mean over the 5 b3_predict folds). The test patients play no part in the choice.
# Writes a NEW file (test_scores_b3.csv); earlier test files stay. Submit with --dependency=afterok:<batch3_predict job>.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
read -r CUT GAUSS PIECE < <(../.venv/bin/python -c "
import glob, json, sys, numpy as np
rows = {}
for f in sorted(glob.glob('runs/b3_predict_fold*/summary.json')):
    for r in json.load(open(f))['rows']:
        rows.setdefault(r['variant'], []).append(r['val_dice'])
for v in sorted(rows):
    print(v, round(float(np.mean(rows[v])), 4), file=sys.stderr)
best = max((v for v in rows if len(rows[v]) == 5), key=lambda v: np.mean(rows[v]))
kind, cut, *piece = best.split('_')
print(cut, '--gauss' if kind == 'gauss' else '-', piece[0] if piece else 'largest')
")
[ "$GAUSS" = "-" ] && GAUSS=""
echo "chosen on validation: cut-off $CUT $GAUSS, piece $PIECE"
[ -n "$CUT" ] || { echo "could not choose a setting (are all 5 b3_predict folds finished?)"; exit 1; }
../.venv/bin/python -u evaluate.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --ours e12_patch_big_fold0 b3_big_fold1 b3_big_fold2 b3_big_fold3 b3_big_fold4 --cutoff "$CUT" $GAUSS --piece "$PIECE" \
    --nnunet-pred ../data/full/pred_nnunet --out ../results/test_scores_b3.csv
