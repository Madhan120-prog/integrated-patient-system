#!/bin/bash
#SBATCH --job-name=anhui_v1_parts
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH --array=0-7
#SBATCH --output=logs/%x_%A_%a.out
# anhui_v1 step 2 only, split over 8 GPUs (the single job was too slow for its 2-day limit). Same recipe, same patients,
# reuses the nnU-Net probabilities anhui_v1 already saved. Nothing is chosen here. Afterwards join the parts:
#   cd ~/tumor-ai/model && ../.venv/bin/python merge_scores.py ../results/anhui_parts/anhui_asls_v1_part*.csv \
#       --expect 447 --out ../results/anhui_asls_v1.csv
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
K=$SLURM_ARRAY_TASK_ID
N=8
for d in data/full/prob_nnunet_resencL/anhui_asls data/full/prob_nnunet_1000ep/anhui_asls; do
    [ "$(ls $d/*.npz 2>/dev/null | wc -l)" -ge 447 ] || { echo "$d: fewer than 447 probability files"; exit 1; }
done
OURS="b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4"
PROB="$PWD/data/full/prob_nnunet_resencL/anhui_asls $PWD/data/full/prob_nnunet_1000ep/anhui_asls"
cd model
../.venv/bin/python -u evaluate.py --data ../data/anhui/nnunet --splits ../data/anhui/splits_asls.json --key test \
    --ours $OURS --gauss --cutoff 0.3 --piece confident --nnunet-prob $PROB --weight 0.25 --part $K/$N \
    --out ../results/anhui_parts/anhui_asls_v1_part$K.csv
