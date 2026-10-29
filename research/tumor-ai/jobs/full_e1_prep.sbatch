#!/bin/bash
#SBATCH --job-name=full_e1_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# nnU-Net's own one-time preparation for the full set, then our patient split. CPU only.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
.venv/bin/nnUNetv2_plan_and_preprocess -d 1 --verify_dataset_integrity -np 8
.venv/bin/python -c "import json; json.dump(json.load(open('data/full/splits.json'))['folds'], open('data/full/nnunet_pre/Dataset001_LungGTV/splits_final.json', 'w'))"
