#!/bin/bash
#SBATCH --job-name=b4_resenc_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# Batch 4: nnU-Net's one-time preparation for its stronger ResEnc L preset. CPU only.
# Writes new files only (nnUNetResEncUNetLPlans.json + its own preprocessed folder); the E1 files stay as they are.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
P=data/full/nnunet_pre/Dataset001_LungGTV
[ -e $P/nnUNetResEncUNetLPlans.json ] && { echo "ResEnc L plans already exist, not overwriting"; exit 1; }
.venv/bin/nnUNetv2_plan_experiment -d 1 -pl nnUNetPlannerResEncL
.venv/bin/nnUNetv2_preprocess -d 1 -plans_name nnUNetResEncUNetLPlans -c 3d_fullres -np 8
