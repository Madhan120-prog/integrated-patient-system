#!/bin/bash
#SBATCH --job-name=e10_nnunet
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%A.out
# E10, the "after" number: nnU-Net ResEnc L, 250 epochs, 5 folds, like b4_resenc (0.638) but trained on Lung1 + new data.
# Validation patients are the same Lung1 ones, so fold scores compare 1:1 with b4_resenc.
# Submit with --dependency=afterok:<e10_nnunet_prep job>. Refuses a fold folder that already holds anything.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_n_proc_DA=8 nnUNet_compile=f
K=$SLURM_ARRAY_TASK_ID
cmp -s data/full/splits_final_multi.json data/full/nnunet_pre/Dataset002_LungMulti/splits_final.json || { echo "our folds are not in place"; exit 1; }
F=runs/nnunet_full/Dataset002_LungMulti/nnUNetTrainer_250epochs__nnUNetResEncUNetLPlans__3d_fullres/fold_$K
[ -n "$(ls -A $F 2>/dev/null)" ] && { echo "$F already has files, not overwriting"; exit 1; }
.venv/bin/nnUNetv2_train 2 3d_fullres $K -tr nnUNetTrainer_250epochs -p nnUNetResEncUNetLPlans
