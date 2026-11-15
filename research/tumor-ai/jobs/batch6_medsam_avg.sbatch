#!/bin/bash
#SBATCH --job-name=b6_medsam_avg
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --array=0-1
#SBATCH --output=logs/%x_task%a_%A.out
# 6.7 / E8 real case, better finder: MedSAM2 with the box from the 6.3 average instead of our U-Net, fold 0 VALIDATION (71).
# Task 0: box from b6_avg_v1's best mix (0.25 x b3_long_fold0 + 0.75 x nnU-Net ResEnc L + 1000 ep, cut-off 0.3, confident).
# Task 1: box from the nnU-Net pair alone (weight 0), same cut-off and piece.
# Compare with b6_medsam_doctor_fold0 (best case, 0.730) and b6_avg_v1_fold0 [w0.25_0.3_confident] (no MedSAM2, 0.687).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai/model
W=0.25; [ "$SLURM_ARRAY_TASK_ID" = 1 ] && W=0
../.venv-medsam2/bin/python -u medsam_box.py --data ../data/full/nnunet/Dataset001_LungGTV --splits ../data/full/splits.json \
    --fold 0 --box ours --ours b3_long_fold0 --ours-setting gauss 0.3 confident \
    --nnunet ../data/full/prob_nnunet_resencL/val_fold0 ../data/full/prob_nnunet_1000ep/val_fold0 \
    --weight $W --name b6_medsam_avg_w${W}_fold0
