#!/bin/bash
#SBATCH --job-name=batch1_e2
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=2-00:00:00
#SBATCH --output=logs/%x_%j.out
# Batch 1, E2: nnU-Net 2D (slice by slice) on fold 0, to compare with nnU-Net 3D fold 0 (val Dice 0.581).
# Its results go to their own folder (..._2d/fold_0); the 3D results are not touched.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_n_proc_DA=8 nnUNet_compile=f
OUT=runs/nnunet_full/Dataset001_LungGTV/nnUNetTrainer_250epochs__nnUNetPlans__2d/fold_0
[ -e "$OUT" ] && { echo "$OUT already exists, so nothing was run (results are never overwritten)."; exit 1; }
[ -d data/full/nnunet_pre/Dataset001_LungGTV/nnUNetPlans_2d ] || .venv/bin/nnUNetv2_preprocess -d 1 -c 2d -np 8
.venv/bin/nnUNetv2_train 1 2d 0 -tr nnUNetTrainer_250epochs
