#!/bin/bash
#SBATCH --job-name=b6_medsam
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-1
#SBATCH --output=logs/%x_task%a_%A.out
# 6.4 / E8: MedSAM2 with a box hint, fold 0 VALIDATION patients (71). Test comes once, at the very end.
# Task 0: (a) box from the doctor's outline = best case. Task 1: (b) box from our U-Net (b3_long_fold0) = real case.
# Needs the separate MedSAM2 environment ~/tumor-ai/.venv-medsam2 and ~/tumor-ai/MedSAM2 (one-time setup, see plan).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
if [ "$SLURM_ARRAY_TASK_ID" = 0 ]; then ARGS="--box doctor --name b6_medsam_doctor_fold0"
else ARGS="--box ours --ours b3_long_fold0 --name b6_medsam_ours_fold0"; fi
../.venv-medsam2/bin/python -u medsam_box.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 $ARGS
