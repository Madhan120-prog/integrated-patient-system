#!/bin/bash
#SBATCH --job-name=batch2_test
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# Final test again, with the prediction setting chosen on VALIDATION (best mean over the 5 e4af_predict folds).
# The test patients play no part in the choice. Writes a NEW file; the first test (test_scores.csv) stays.
# Submit with --dependency=afterok:<job number of batch1_predict> so it waits for all 5 folds.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
read -r CUT GAUSS < <(../.venv/bin/python -c "
import glob, json, numpy as np
rows = {}
for f in sorted(glob.glob('runs/e4af_predict_fold*/summary.json')):
    for r in json.load(open(f))['rows']:
        rows.setdefault(r['variant'], []).append(r['val_dice'])
best = max((v for v in rows if len(rows[v]) == 5), key=lambda v: np.mean(rows[v]))
for v in sorted(rows):
    print(v, round(float(np.mean(rows[v])), 4), file=__import__('sys').stderr)
kind, cut = best.split('_')
print(cut, '--gauss' if kind == 'gauss' else '')
")
echo "chosen on validation: cut-off $CUT $GAUSS"
[ -n "$CUT" ] || { echo "could not choose a setting (are all 5 e4af_predict folds finished?)"; exit 1; }
../.venv/bin/python -u evaluate.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --ours full_e3_fold0 full_e3_fold1 full_e3_fold2 full_e3_fold3 full_e3_fold4 --cutoff "$CUT" $GAUSS \
    --nnunet-pred ../data/full/pred_nnunet --out ../results/test_scores_cutoff.csv
