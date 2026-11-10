#!/bin/bash
#SBATCH --job-name=b6_e7
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-2
#SBATCH --output=logs/%x_task%a_%A.out
# 6.5 / E7: pre-trained vs from scratch. Swin UNETR whose encoder starts from MONAI's self-supervised weights
# (learned on ~5,000 CTs, model_swinvit.pt) against the same Swin from scratch. Same settings as b4_swin_big_fold0
# (Swin, block 64x192x192, lr 1e-4, 50,000 steps, fold 0, seed 42: 0.531), so the start is the only change.
# Task 2 repeats from-scratch with seed 7, giving 2 runs per side. Needs ~/tumor-ai/weights/model_swinvit.pt (see plan).
RUNS=(
  "b6_swin_pre_fold0|E7|Swin, encoder pre-trained on ~5,000 CTs|--pretrained ../weights/model_swinvit.pt"
  "b6_swin_pre_seed7_fold0|E7|Swin, encoder pre-trained on ~5,000 CTs, seed 7|--pretrained ../weights/model_swinvit.pt --seed 7"
  "b6_swin_scratch_seed7_fold0|E7|Swin from scratch, seed 7 (second run of b4_swin_big_fold0)|--seed 7"
)
IFS='|' read -r NAME EXP CHANGE EXTRA <<< "${RUNS[$SLURM_ARRAY_TASK_ID]}"
echo "task $SLURM_ARRAY_TASK_ID: $NAME ($EXP) $CHANGE | $EXTRA"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --steps 50000 --val-every 5000 --arch swin --patch 64 192 192 --lr 1e-4 \
    --name "$NAME" --exp "$EXP" --change "$CHANGE" $EXTRA
