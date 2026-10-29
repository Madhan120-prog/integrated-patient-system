# Tumor AI: learning guide and experiment plan

Goal: train AI models that **find and outline lung tumours on CT**, compare them fairly,
and later explain each result at different levels (patient, doctor, physicist ...).
This folder is a separate experiment. It does not touch the portal.

Data: NSCLC-Radiomics (TCIA, ~420 patients, CT + tumour outlines by radiation oncologists).
Licence CC BY-NC 3.0, cite: Aerts et al., doi:10.7937/K9/TCIA.2015.PF0M9REI.

---

## 0. Where to start (in this order)

| # | Do this | Where | Done when |
|---|---|---|---|
| 1 | Run the pipeline on the 6 patients we already have | your Mac | `data/qc/` pictures show red masks on the tumours ✅ (done) |
| 2 | Set up a Python environment on HPC, copy this folder there | HPC | `python model/unet3d.py` prints `ok` |
| 3 | Download patients to HPC scratch storage (`prep/00_download.py`; start with 50, see `plan.md`) | HPC | 50 patients = 3.0 GB, all 422 = 27.5 GB |
| 4 | Run steps 1 to 3 below on the full set, then **look at every QC picture** | HPC | `inventory.csv`, `cases.csv`, `splits.json` |
| 5 | Experiment E0: train on 1 patient until it is perfect | HPC | Dice near 1.0 (proves the pipeline) |
| 6 | Experiment E1: nnU-Net baseline | HPC | a real score to beat |
| 7 | Experiment E3: our own U-Net, same split | HPC | first comparison |

Commands (from this folder):

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python prep/00_download.py data/raw --patients 50
.venv/bin/python prep/01_inventory.py data/raw data/inventory.csv
.venv/bin/python prep/02_convert.py data/inventory.csv data
.venv/bin/python prep/03_split.py data/cases.csv data/splits.json
cd model && ../.venv/bin/python train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits.json --fold 0
```

---

## 1. The pipeline, step by step: what, how, why

### Step 1: data check (`prep/01_inventory.py`)
**What:** reads only the *labels on* each DICOM file (no pictures) and writes one row per patient:
number of slices, slice spacing, pixel size, scanner make, outline names, "is the main tumour outlined?",
and a list of problems.

**Why:** real data has holes. In this dataset: patient LUNG1-128 has no tumour outline (post-surgery
scan), some patients have extra outlines `gtv-2`, `gtv-3` (usually lymph nodes), some lack heart outlines,
scans come from two makers. Training on a broken case silently teaches the model wrong things.
Finding problems costs seconds here and days later.

**How it decides things:**
- Files are grouped by what their headers say (patient ID, series ID), so any folder layout works.
- The CT used is the one the outline file *points to*, not a guess.
- "Uneven slice spacing" flags missing slices.

### Step 2: convert to model-ready files (`prep/02_convert.py`)
**What:** for each clean patient:
- **CT:** ~110 DICOM files → one 3D file `imagesTr/LUNG1-001_0000.nii.gz`.
  Values stay in **Hounsfield units (HU)**, the standard CT density scale: air −1000, water 0, bone +400 and up.
- **Mask:** the doctor's GTV-1 outline (a list of points per slice) → a 3D grid of 0/1 the same size as the CT,
  `labelsTr/LUNG1-001.nii.gz`. This is the "answer key" the model learns from.
- **Check picture** in `data/qc/`: the slice where the tumour is largest, tumour in red.
- `cases.csv`: tumour volume and slice count per patient (used for the split and later for "how does it do on small tumours?").

**Why NIfTI (.nii.gz):** one file per scan instead of ~110, compressed, keeps spacing and position,
and it is what nnU-Net, MONAI and most papers use. HPC disks are slow with tens of thousands of small files.

**Why we only use GTV-1 at first:** one clear question ("outline the main tumour"). Lymph nodes are a
second, harder task for later.

**How the mask is made:** each outline point (in mm) is turned into a pixel position on the CT grid,
the polygon is filled, and contours inside contours become holes. Single-point markers are skipped.

**Why the QC pictures matter:** this dataset once had outlines shifted against the scans (fixed in a later
release). A misaligned mask looks fine in numbers and wrong in a picture. Look at every one.

### Step 3: split by patient (`prep/03_split.py`)
**What:** ~15% of patients go to a **locked test set**. The rest are dealt into **5 folds**.
**Why by patient:** neighbouring slices of one patient look almost identical. If some go to training and
some to testing, the model is tested on what it has already seen and the score is falsely high. This is
the most common mistake in published work.
**Why balanced by tumour size:** small tumours are much harder. Every group gets small and large ones,
so one unlucky fold doesn't decide the result.
**Why 5 folds:** each model is trained 5 times, each time checked on a different fifth. The average and
spread tell you if a difference between two models is real or luck.
**Rule:** the test set is used **once**, at the end, for the final table.

### Step 4: feeding the model (inside `model/train.py`)
| Step | What we do | Why |
|---|---|---|
| Clip HU to −1000..500 | ignore values above dense soft tissue | bone and metal add nothing for lung tumours and would squash the useful range |
| Scale to −1..1 | divide into a small, steady range | networks learn faster on small numbers |
| 3D blocks of 32 × 128 × 128 | cut random blocks, not whole scans | a whole scan doesn't fit in GPU memory |
| 1 in 3 blocks centred on tumour | force the model to see tumours | tumour is under 1% of the scan; otherwise it learns "always say no" |
| Brightness, contrast, noise jitter | small random changes each time | the model sees "new" examples and doesn't memorise |
| **No left-right flip** | deliberately off | left and right lungs differ (heart side); a study on this dataset found flipping hurt |

### Step 5: the network (`model/unet3d.py`)
**Why a U-Net:** it is the standard design for outlining things in medical images since 2015, still the
backbone of most winners. It does two jobs that outlining needs:
- the **encoder** shrinks the scan step by step and learns *what* is there (tumour vs vessel vs heart),
- the **decoder** grows it back and learns *where* exactly,
- **skip connections** pass fine detail across, so edges stay sharp.

**Why 3D, not 2D:** a tumour and a blood vessel can look the same on one slice; across slices a vessel is a
tube and a tumour is a ball. 3D sees that.

**Our specific choices:**
- slices are 3 mm apart but pixels ~1 mm, so the first shrink is only in-plane (1,2,2); then voxels are nearly cubes.
- InstanceNorm + LeakyReLU, two 3×3×3 convolutions per level: nnU-Net's tested defaults.
- 1.4 million parameters at `--base 16` (use `--base 32` on HPC, about 4× more).

### Step 6: training (`model/train.py`)
- **Loss = cross-entropy + Dice.** Cross-entropy judges every voxel; Dice judges the overlap of the tumour as
  a whole. Dice alone is unstable, cross-entropy alone ignores tiny tumours. Together is the standard.
- **AdamW, learning rate 3e-4, slowly lowered to zero.** A safe, common choice. (nnU-Net uses SGD; comparing
  the two is itself an experiment.)
- Every `--val-every` steps it outlines the whole validation scans and saves the best weights (`best.pt`).

### Step 7: measuring (what goes in the results table)
| Measure | Meaning | Good |
|---|---|---|
| **Dice** | overlap of AI and doctor outline, 0 to 1 | ~0.8 is doctor-vs-doctor level for lung GTV |
| **HD95** (mm) | how far off the edge is, ignoring the worst 5% | lower is better |
| **Volume difference** (%) | AI tumour bigger or smaller than the doctor's | near 0 |
| **Detection rate** | tumour found at all (Dice > 0.1) | near 100% |
| **Dice by size group** | small / medium / large tumours separately | shows where it fails |
| Time and GPU memory | cost of the model | for the "is it practical?" question |

---

## 2. Train from scratch or use a pre-trained model?

| | From scratch | Pre-trained, then fine-tuned |
|---|---|---|
| Starts with | random weights | weights learned from thousands of other CT scans |
| Needs | more data and training time | less data, often faster to a good result |
| Understand it fully? | yes, every part is ours | partly, the starting point came from elsewhere |
| Examples | our U-Net, nnU-Net (also trains from scratch) | CT models trained on large organ datasets (e.g. STU-Net, SuPreM), MedSAM (click-to-outline) |

**Plan:** start from scratch (our U-Net and nnU-Net) so we have clean baselines, then add a pre-trained model
as its own experiment (E7). "Does pre-training help on ~400 patients?" is a real research question.

---

## 3. Running on HPC

Example job file (`job.sh`). Partition, account and module names differ per university, check your HPC docs:

```bash
#!/bin/bash
#SBATCH --job-name=lung-gtv-fold0
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=24:00:00
#SBATCH --output=logs/%x_%j.out
cd $SLURM_SUBMIT_DIR/model
../.venv/bin/python train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits.json \
    --fold 0 --base 32 --patch 48 160 160 --steps 50000 --name unet3d_b32_fold0
```

nnU-Net baseline (same data folder, same split):

```bash
pip install nnunetv2
export nnUNet_raw=$PWD/data/nnunet nnUNet_preprocessed=$PWD/data/nnunet_pre nnUNet_results=$PWD/runs/nnunet
nnUNetv2_plan_and_preprocess -d 1 --verify_dataset_integrity
python -c "import json; json.dump(json.load(open('data/splits.json'))['folds'], open('data/nnunet_pre/Dataset001_LungGTV/splits_final.json','w'))"
nnUNetv2_train 1 3d_fullres 0      # fold 0; repeat for 1..4
```

Test patients are in no fold, so neither model ever trains on them.

**Data rule:** only public data on HPC. Clinic data (for example Dr. Pradeep's case) stays off it until the
hospital and university both approve.

---

## 4. Experiment table

Every run: same `splits.json`, seed recorded, results added as one row to `results.csv`.

| ID | Question | Model / change | Data | Main measure | Notes |
|---|---|---|---|---|---|
| **E0** | Does the pipeline work at all? | our U-Net, train and test on 1 patient | 1 patient | Dice → ~1.0 | if not, there's a bug, not a research result |
| **E1** | What is the strong baseline? | nnU-Net 3d_fullres | Lung1, 5 folds | Dice, HD95 | the number to beat |
| **E2** | Does 3D beat 2D? | nnU-Net 2d vs 3d_fullres | Lung1 | Dice by size | expect 3D better on small tumours |
| **E3** | How does our own design do? | our U-Net, base 32 | Lung1 | all | first comparison with E1 |
| **E4** | Can we help small tumours? | our U-Net + one change (e.g. deep supervision, attention gates, Tversky loss) | Lung1 | Dice on small tumours | one change at a time |
| **E5** | Find first, then outline? | two-stage: locate tumour box, then outline inside it | Lung1 | detection rate, Dice | newest papers use this |
| **E6** | Do transformers help? | Swin UNETR (MONAI) | Lung1 | all + GPU memory | heavier model |
| **E7** | Does pre-training help? | pre-trained CT model, fine-tuned vs from scratch | Lung1 | Dice vs training time | |
| **E8** | How good is click-to-outline? | MedSAM with a box around the tumour | Lung1 | Dice | a "doctor helps AI" setting |
| **E9** | How much data do we need? | best model on 25 / 50 / 100% of training patients | Lung1 | Dice curve | tells whether more data is worth chasing |
| **E10** | Does more data help? | best model + NSCLC-Radiogenomics + Decathlon Lung | combined | Dice | same label meaning only |
| **E11** | Does it work on unseen hospitals' scans? | train on Lung1, test on Radiogenomics | external | Dice drop | key question for doctors |
| **E12** | Which preprocessing matters? | HU window, flip on/off, block size | Lung1 | Dice | small ablation runs |
| **E13** | Do outline errors change the dose? | AI vs doctor outline through the dose code | later, with plans | dose difference (Gy) | our distinctive question |

`results.csv` columns: `id, model, data, fold, seed, dice, hd95_mm, vol_diff_pct, detect_rate, dice_small, dice_large, train_hours, gpu_gb, notes`

---

## 5. Folder layout

```
prep/00_download.py    download from TCIA
prep/01_inventory.py   data check
prep/02_convert.py     DICOM -> NIfTI + masks + QC pictures
prep/03_split.py       patient-level split
model/unet3d.py        our network (run it alone for a self-check)
model/train.py         training and validation
data/                  generated, never committed
runs/                  model weights and logs, never committed
```
