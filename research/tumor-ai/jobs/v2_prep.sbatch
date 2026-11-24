#!/bin/bash
#SBATCH --job-name=v2_prep
#SBATCH --partition=acomputeq
#SBATCH --cpus-per-task=16
#SBATCH --mem=96G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# v2 data (CPU), after anhui_prep: lock the new Anhui test slice and build Dataset003_LungV2 (prep/14_v2.py), then nnU-Net
# preparation with Dataset001's ResEnc L plan unchanged (same as E10: only the data changes), then OUR folds.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
set -e
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
P=data/full/nnunet_pre/Dataset003_LungV2
[ -n "$(ls -A $P 2>/dev/null)" ] && { echo "$P already has files, not overwriting"; exit 1; }
.venv/bin/python prep/14_v2.py data/full data/anhui
mkdir -p $P
.venv/bin/nnUNetv2_extract_fingerprint -d 3 --verify_dataset_integrity -np 8
.venv/bin/nnUNetv2_move_plans_between_datasets -s 1 -t 3 -sp nnUNetResEncUNetLPlans -tp nnUNetResEncUNetLPlans
cp data/full/nnunet/Dataset003_LungV2/dataset.json $P/    # moving plans does not copy it
.venv/bin/nnUNetv2_preprocess -d 3 -plans_name nnUNetResEncUNetLPlans -c 3d_fullres -np 8
cp data/full/splits_final_v2.json $P/splits_final.json
.venv/bin/python -c "
import json
a, b = (json.load(open(f'data/full/nnunet_pre/{d}/nnUNetResEncUNetLPlans.json'))['configurations']['3d_fullres'] for d in ('Dataset001_LungGTV', 'Dataset003_LungV2'))
print('spacing', a['spacing'], b['spacing'], '| block', a['patch_size'], b['patch_size'])
assert a['spacing'] == b['spacing'] and a['patch_size'] == b['patch_size'], 'plans differ'"
