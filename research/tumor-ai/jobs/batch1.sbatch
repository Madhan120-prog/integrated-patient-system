#!/bin/bash
#SBATCH --job-name=batch1
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --array=0-9
#SBATCH --output=logs/%x_task%a_%A.out
# Batch 1: independent experiments, fold 0 only, each ONE change from E3 fold 0 (val Dice 0.450).
# Same patients, seed, steps (50,000) and block size as E3 unless the change says otherwise.
# Slurm keeps its own copy of this file when you submit, so editing it later never changes queued runs.
# Each run writes runs/<name>/ and refuses to start if that folder already holds anything.
RUNS=(
  "e4b_deepsup_fold0|E4b|deep supervision|--deep-sup"
  "e4c_moreaug_fold0|E4c|+ rotation, zoom, gamma augmentation|--aug more"
  "e4d_zscore_fold0|E4d|nnU-Net brightness scaling (tumour percentiles + z-score)|--norm zscore"
  "e4e_bigger_fold0|E4e|5 levels, channels up to 320|--levels 5"
  "e6_swin_fold0|E6|Swin UNETR transformer instead of our U-Net|--arch swin --patch 64 160 160 --lr 1e-4"
  "e9_frac25_fold0|E9|only 25% of the training patients|--frac 0.25"
  "e9_frac50_fold0|E9|only 50% of the training patients|--frac 0.5"
  "e12_hu_wide_fold0|E12|wider HU window -1000..1000|--hu -1000 1000"
  "e12_flip_fold0|E12|left-right flip augmentation on|--flip"
  "e12_patch_big_fold0|E12|bigger block 64x192x192|--patch 64 192 192"
)
IFS='|' read -r NAME EXP CHANGE EXTRA <<< "${RUNS[$SLURM_ARRAY_TASK_ID]}"
echo "task $SLURM_ARRAY_TASK_ID: $NAME ($EXP) $CHANGE | $EXTRA"
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
../.venv/bin/python -u train.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --base 32 --patch 48 160 160 --steps 50000 --val-every 5000 \
    --name "$NAME" --exp "$EXP" --change "$CHANGE" $EXTRA
