#!/bin/bash
#SBATCH --job-name=e10_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=08:00:00
#SBATCH --output=logs/%x_%j.out
# E10/E11 data preparation (CPU), AFTER both downloads finished on the login node (see plan.md "E10 now"):
#   Radiogenomics CT + SEG -> NIfTI, MSD Lung -> NIfTI (both oriented like Lung1), QC pictures,
#   then the combined Dataset002_LungMulti + splits_multi.json (outside test A locked; Lung1 folds/test unchanged).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
.venv/bin/python prep/10_radiogenomics.py convert data/radiogenomics/raw data/radiogenomics
.venv/bin/python prep/11_msd_lung.py convert data/msd_lung/raw data/msd_lung
.venv/bin/python prep/12_combine.py data/full data/radiogenomics data/msd_lung
