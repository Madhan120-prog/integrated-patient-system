#!/bin/bash
#SBATCH --job-name=anhui_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=4
#SBATCH --mem=32G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# Outside test 2: Anhui Chest Hospital ASLS26 (449 advanced-stage patients, radiotherapy GTVs by 2+ oncologists, CC0).
# First copy ASLS26.zip (downloaded in a browser) to ~/tumor-ai/data/anhui/. Unzips, converts, QC pictures, cases.csv,
# data/anhui/splits_asls.json ("test" = usable patients). Refuses to run twice.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
[ -f data/anhui/ASLS26.zip ] || { echo "copy ASLS26.zip to data/anhui/ first"; exit 1; }
[ -e data/anhui/splits_asls.json ] && { echo "already converted"; exit 1; }
[ -d data/anhui/raw/ASLS26 ] || .venv/bin/python prep/13_anhui.py unzip data/anhui/ASLS26.zip data/anhui/raw
.venv/bin/python prep/13_anhui.py convert data/anhui/raw/ASLS26 data/anhui ASLS
