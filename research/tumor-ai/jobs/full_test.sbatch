#!/bin/bash
#SBATCH --job-name=full_test
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=12:00:00
#SBATCH --output=logs/%x_%j.out
# Final test on the locked test patients: nnU-Net (5 folds averaged) and our U-Net (5 folds averaged).
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/full/nnunet nnUNet_preprocessed=$PWD/data/full/nnunet_pre nnUNet_results=$PWD/runs/nnunet_full
export nnUNet_compile=f
D=data/full/nnunet/Dataset001_LungGTV
mkdir -p data/full/test_images
.venv/bin/python -c "import json, os; [os.symlink(os.path.abspath(f'$D/imagesTr/{p}_0000.nii.gz'), f'data/full/test_images/{p}_0000.nii.gz') for p in json.load(open('data/full/splits.json'))['test'] if not os.path.exists(f'data/full/test_images/{p}_0000.nii.gz')]"
.venv/bin/nnUNetv2_predict -i data/full/test_images -o data/full/pred_nnunet -d 1 -c 3d_fullres -tr nnUNetTrainer_250epochs -f 0 1 2 3 4
cd model
../.venv/bin/python -u evaluate.py --data ../$D --splits ../data/full/splits.json \
    --ours full_e3_fold0 full_e3_fold1 full_e3_fold2 full_e3_fold3 full_e3_fold4 \
    --nnunet-pred ../data/full/pred_nnunet --out ../results/test_scores.csv
