#!/bin/bash
#SBATCH --job-name=e10_nnunet_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# E10: nnU-Net's one-time preparation (ResEnc L preset) for Dataset002_LungMulti (Lung1 non-test + Radiogenomics B + MSD),
# then OUR folds (splits_final_multi.json: extra cases on the training side only, validation = the same Lung1 patients).
# CPU only. Dataset001 files are not touched.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
P=data/full/nnunet_pre/Dataset002_LungMulti
[ -e $P/nnUNetResEncUNetLPlans.json ] && { echo "Dataset002 plans already exist, not overwriting"; exit 1; }
.venv/bin/nnUNetv2_plan_and_preprocess -d 2 -pl nnUNetPlannerResEncL -c 3d_fullres --verify_dataset_integrity -np 8
cp data/full/splits_final_multi.json $P/splits_final.json
grep -A3 '"spacing"' $P/nnUNetResEncUNetLPlans.json | head -5    # target spacing: compare with Dataset001's
