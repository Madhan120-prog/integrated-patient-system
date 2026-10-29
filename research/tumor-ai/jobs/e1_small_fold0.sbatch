#!/bin/bash
#SBATCH --job-name=e1_small_fold0
#SBATCH --partition=agpuq
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=48G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out
# E1-small: nnU-Net baseline, fold 0, same 50-patient split as our U-Net, shortened to 100 epochs.
module load python/3.12.9/gcc.8.5.0
cd ~/tumor-ai
export nnUNet_raw=$PWD/data/nnunet nnUNet_preprocessed=$PWD/data/nnunet_pre nnUNet_results=$PWD/runs/nnunet
export nnUNet_n_proc_DA=8
export nnUNet_compile=f   # torch.compile crashed on BigBlue (torch 2.15, job 3516113); run without it
.venv/bin/nnUNetv2_plan_and_preprocess -d 1 --verify_dataset_integrity
.venv/bin/python -c "import json; json.dump(json.load(open('data/splits.json'))['folds'], open('data/nnunet_pre/Dataset001_LungGTV/splits_final.json', 'w'))"
.venv/bin/nnUNetv2_train 1 3d_fullres 0 -tr nnUNetTrainer_100epochs
