#!/bin/bash
#SBATCH --job-name=levels_outside
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-8
#SBATCH --output=logs/%x_%A_%a.out
# The four-level explanation checks (paper Table III) at the two OUTSIDE hospitals, v1 unchanged, cut-off 0.3.
# This was step 3 of anhui_v1, lost when that job was cancelled. Describing only, nothing chosen.
# Split over 9 GPUs (~1.5 min per patient): tasks 0-7 = outside B (Anhui ASLS26, 447 patients) in 8 parts,
# task 8 = outside A (NSCLC-Radiogenomics, 72 patients). Code runs from the git clone (~/ips). Refuses to overwrite.
module load python/3.12.9/gcc.8.5.0
set -e
T=~/tumor-ai
P=$T/data/full
K=$SLURM_ARRAY_TASK_ID
OURS="b3_long_fold0 b5_long_fold1 b5_long_fold2 b5_long_fold3 b5_long_fold4"
TXT="25% our U-Net + 75% nnU-Net (ResEnc L 250 ep + nnU-Net 1000 ep), 5 folds"
mkdir -p $T/results/levels_parts
cd ~/ips/research/tumor-ai/prototype
if [ "$K" = 8 ]; then
  $T/.venv/bin/python -u levels_eval.py --set outside --key outside_test --data $P/outside_A --splits $P/splits_multi.json \
      --runs $T/model/runs --cut 0.3 --ours $OURS --nnunet-prob $P/prob_nnunet_resencL/outside_A $P/prob_nnunet_1000ep/outside_A \
      --model-text "$TXT" --out $T/results/levels_eval_outside_A.csv
else
  $T/.venv/bin/python -u levels_eval.py --set outside --part $K/8 --data $T/data/anhui/nnunet --splits $T/data/anhui/splits_asls.json \
      --runs $T/model/runs --cut 0.3 --ours $OURS --nnunet-prob $P/prob_nnunet_resencL/anhui_asls $P/prob_nnunet_1000ep/anhui_asls \
      --model-text "$TXT" --out $T/results/levels_parts/levels_eval_anhui_asls_part$K.csv
fi
