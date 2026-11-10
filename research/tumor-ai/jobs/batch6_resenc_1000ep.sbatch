#!/bin/bash
#SBATCH --job-name=b6_resenc_1000ep
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=3-00:00:00
#SBATCH --array=0-4
#SBATCH --output=logs/%x_fold%a_%A.out
# 6.1: nnU-Net ResEnc L at its normal 1000 epochs (b4_resenc used 250), 5 folds: our two best nnU-Net gains together.
# Uses the ResEnc L plans already prepared by b4_resenc_prep. Writes its own folder; refuses a fold folder that holds anything.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_n_proc_DA=8 nnUNet_compile=f
K=$SLURM_ARRAY_TASK_ID
F=runs/nnunet_full/Dataset001_LungGTV/nnUNetTrainer__nnUNetResEncUNetLPlans__3d_fullres/fold_$K
[ -n "$(ls -A $F 2>/dev/null)" ] && { echo "$F already has files, not overwriting"; exit 1; }
.venv/bin/nnUNetv2_train 1 3d_fullres $K -tr nnUNetTrainer -p nnUNetResEncUNetLPlans
