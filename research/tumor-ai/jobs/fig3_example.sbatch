#!/bin/bash
#SBATCH --job-name=fig3_example
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=48G
#SBATCH --time=02:00:00
#SBATCH --output=logs/%x_%j.out
# Paper Fig. 3: one real fold-0 VALIDATION patient's fact sheet and texts, exactly as levels_eval_v2 (fold-0 models, v1
# weights, cut-off 0.3). CPU only (one patient), so it does not wait for a GPU.
# Patient chosen by a fixed rule from results/levels_eval_fold0_v2.csv (2026-11-28): doctor's outline 20-100 cc, same side
# and same part as the doctor, Dice closest to the fold-0 median (0.825) -> LUNG1-374 (Dice 0.823). Not cherry-picked.
module load python/3.12.9/gcc.8.5.0
set -e
T=~/tumor-ai
P=$T/data/full
cd ~/ips/research/tumor-ai/prototype
$T/.venv/bin/python -u levels_eval.py --set fold0 --patients LUNG1-374 \
    --data $P/nnunet/Dataset001_LungGTV --splits $P/splits.json --runs $T/model/runs --cut 0.3 --ours b3_long_fold0 \
    --nnunet-prob $P/prob_nnunet_resencL/val_fold0 $P/prob_nnunet_1000ep/val_fold0 \
    --model-text "25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep), fold 0" \
    --out $T/results/fig3_example.csv --dump $T/results/fig3_example.json
