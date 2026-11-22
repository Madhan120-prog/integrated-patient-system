#!/bin/bash
#SBATCH --job-name=e10_nnunet_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# E10: nnU-Net preparation for Dataset002_LungMulti (Lung1 non-test + Radiogenomics B + MSD), then OUR folds
# (splits_final_multi.json: extra cases on the training side only, validation = the same Lung1 patients). CPU only.
# Uses Dataset001's ResEnc L PLAN unchanged (same slice spacing, block size, network, brightness scaling), so the data is
# the only change vs b4_resenc. Planning afresh would pick 1.25 mm slices instead of Lung1's (most new scans are thin),
# which would change two things at once. Dataset001 files are not touched.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
P=data/full/nnunet_pre/Dataset002_LungMulti
[ -n "$(ls -A $P 2>/dev/null)" ] && { echo "$P already has files, not overwriting"; exit 1; }
mkdir -p $P
.venv/bin/nnUNetv2_extract_fingerprint -d 2 --verify_dataset_integrity -np 8
.venv/bin/nnUNetv2_move_plans_between_datasets -s 1 -t 2 -sp nnUNetResEncUNetLPlans -tp nnUNetResEncUNetLPlans
cp data/full/nnunet/Dataset002_LungMulti/dataset.json $P/    # planning normally copies it; moving plans does not
.venv/bin/nnUNetv2_preprocess -d 2 -plans_name nnUNetResEncUNetLPlans -c 3d_fullres -np 8
cp data/full/splits_final_multi.json $P/splits_final.json
.venv/bin/python -c "
import json
a, b = (json.load(open(f'data/full/nnunet_pre/{d}/nnUNetResEncUNetLPlans.json'))['configurations']['3d_fullres'] for d in ('Dataset001_LungGTV', 'Dataset002_LungMulti'))
print('spacing', a['spacing'], b['spacing'], '| block', a['patch_size'], b['patch_size'])
assert a['spacing'] == b['spacing'] and a['patch_size'] == b['patch_size'], 'plans differ'"
