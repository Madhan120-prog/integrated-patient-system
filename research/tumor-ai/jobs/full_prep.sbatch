#!/bin/bash
#SBATCH --job-name=full_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=06:00:00
#SBATCH --output=logs/%x_%j.out
# All 422 patients: data check, DICOM -> NIfTI + masks + QC pictures, patient split. Writes to data/full/.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
.venv/bin/python prep/01_inventory.py data/raw data/full/inventory.csv
.venv/bin/python prep/02_convert.py data/full/inventory.csv data/full
.venv/bin/python prep/03_split.py data/full/cases.csv data/full/splits.json
