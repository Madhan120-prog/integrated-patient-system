# Lung Tumor Detection and Outlining with AI: plan

> Last updated: 2026-10-27
> Goal: prove the whole loop works on **50 patients** before spending days of GPU time on all 422.
> The learning guide and experiment table are in `README.md`; this file is the order of work.

## Experiment tracker
Live page: https://claude.ai/artifact/3SiwC4T6AfLfb8jw2VV39y (private until shared). Its data files are kept in `results/experiments.json` and `results/training_curves.json`; update both after each run.

## How to work on HPC: which tool for what

| Tool | What it is | Use it for | Don't use it for |
|---|---|---|---|
| **Open OnDemand** (web page, if your HPC offers it; most do) | HPC in the browser: file browser, Jupyter, VS Code in the browser, job list | **Recommended start.** Interactive GPU sessions for short tests, looking at QC pictures, editing files | Runs longer than the session time limit |
| **VS Code Remote-SSH** (from your Mac) | Your normal VS Code, but the files live on HPC | Comfortable editing and submitting jobs | Training: it connects to the *login node*, which is shared; heavy work there is usually banned |
| **SSH + `sbatch`** (terminal) | Send a job to the queue; it runs on a GPU node while you're away | **All long training runs** (hours to days) | Quick trial and error |

**Suggested setup:** learn and test in **OnDemand** (Jupyter or VS Code app on a GPU node), then send real
training as **`sbatch` jobs**. If you prefer your own VS Code, use Remote-SSH for editing and `sbatch` for running.

## Our HPC: BigBlue (University of Memphis)
- OnDemand: https://bigblueweb.memphis.edu (Files, Jobs, Clusters → shell, Interactive Apps: VSCode, Jupyter)
- GPUs: 12 × V100 (Intel nodes), 8 × A100 (AMD nodes); scheduler SLURM
- Confirmed 2026-10-28 with `sinfo`: `agpuq` = 4 nodes × 2 GPUs (A100), max 17 days; `igpuq` = 6 nodes × 2 GPUs (V100). Request with `--gres=gpu:1`
- Python: `module load python/3.12.9/gcc.8.5.0` (load it before every use of `.venv`)
- Quotas: home 50 GB, project 1 TB, scratch 10 TB. Scratch: `/scratch/$USER` (not backed up). Internet works from the login node
- Help: hpcadmins@memphis.edu

## Check these on your HPC first (one-time, ~30 min, from its user docs or help desk)
- [ ] Is there **Open OnDemand**? What's its web address?
- [ ] Name of the **GPU partition** and the GPU type (A100, V100, ...), and the **max job time**
- [ ] **Storage:** home quota, and the **scratch** path (big, fast, but often auto-deleted after N days)
- [ ] Do **compute nodes have internet**? Often they don't, so downloads run on the login node or a "data transfer node"
- [ ] How to load Python / CUDA (`module avail python`, `module avail cuda`)

## Phase A: done on your Mac ✅
- [x] Pipeline written: download, data check, conversion + QC pictures, patient split
- [x] Own 3D U-Net and training script
- [x] Tested on 6 local patients; QC pictures confirmed masks sit on the tumours
- [x] Download tested with 1 patient from TCIA

## Phase B: set up on HPC (day 1)
- [x] Copy the code (not data) to HPC (done 2026-10-28 by uploading `tumor-ai-code.zip` in OnDemand Files), or from the project root on your Mac:
  `rsync -av --exclude data --exclude runs --exclude .venv research/tumor-ai/ <you>@<hpc-address>:~/tumor-ai/`
- [x] On HPC: `cd ~/tumor-ai && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- [x] Point `data/` at scratch so big files don't fill your home quota:
  `mkdir -p <scratch>/tumor-ai-data && ln -s <scratch>/tumor-ai-data data`
- [x] Self-check on a GPU node (A100 80 GB, `GPU ready: True`): `.venv/bin/python model/unet3d.py` → prints `ok`

## Phase C: 50 patients of data (day 1-2)
- [x] Download (login / transfer node): `.venv/bin/python prep/00_download.py data/raw --patients 50` → 100 series, 0 failed, 5.7 GB on disk, 5,664 files (API size 3.0 GB understates it)
- [x] Data check: `.venv/bin/python prep/01_inventory.py data/raw data/inventory.csv`
- [x] Convert (48 converted; skipped LUNG1-014 and LUNG1-021, 021 = uneven slice spacing 3-6 mm): `.venv/bin/python prep/02_convert.py data/inventory.csv data`
- [x] **Open every picture in `data/qc/`** (OnDemand file browser). All 48 sit on a lesion. Very small: LUNG1-027 (1.0 cc), 049 (3.0 cc), 050 (6.5 cc)
- [x] Split: `.venv/bin/python prep/03_split.py data/cases.csv data/splits.json` → 7 test, 41 in 5 folds

## Phase D: E0, "can it learn one patient?" (day 2, ~30 min, interactive) ✅
Done 2026-10-28 on A100: Dice 0.16 (step 250) → 0.90 (step 2,000). Pipeline and GPU proven.
Train and validate on the same single patient. Dice should climb towards 1.0. If it doesn't, there is a bug.
```bash
python -c "import json; json.dump({'test': [], 'folds': [{'train': ['LUNG1-001'], 'val': ['LUNG1-001']}]}, open('data/splits_e0.json', 'w'))"
cd model && ../.venv/bin/python train.py --data ../data/nnunet/Dataset001_LungGTV --splits ../data/splits_e0.json --steps 2000 --val-every 250 --name e0_overfit
```

## Phase E: first two real runs, fold 0 only (day 2-4, batch jobs)
| Run | Command (inside an `sbatch` job, see README section 3) | Rough time on one modern GPU |
|---|---|---|
| **E3-small**: our U-Net (`jobs/e3_small_fold0.sbatch`) | `train.py ... --fold 0 --base 32 --patch 48 160 160 --steps 20000 --name e3_small_fold0` | a few hours |
| **E1-small**: nnU-Net, shortened (`jobs/e1_small_fold0.sbatch`) | `nnUNetv2_plan_and_preprocess -d 1` then `nnUNetv2_train 1 3d_fullres 0 -tr nnUNetTrainer_100epochs` | a few hours |

(Times are estimates; the first run tells us the real speed. Use the same `splits.json` for both, see README section 3.)

- Submitted 2026-10-28: E3-small = job 3516111 (ag01), E1-small = job 3516113 (ag02, nnunetv2 2.8.1); both started. E1 crashed at training start (torch.compile error: "Attempting to use a closed pool"); preprocessing finished; rerun with `nnUNet_compile=f`. E3 step 1,000: val Dice 0.10 (normal this early)
- [ ] Record both in `results.csv` (columns in README section 4)
- [ ] Look at 3-4 predicted outlines next to the doctor's, especially one small tumour

## Phase F: review, then scale (end of week 1)
- [ ] Show Dr. Dasgupta: QC pictures, E0 curve, E1 vs E3 on 50 patients
- [ ] Decide: fix anything found, then download all 422 (27.5 GB) and run all 5 folds of E1 and E3
- [ ] Then continue with the experiment table (E2, E4 ...)

- [x] Full runs done 2026-10-30: E1 and E3 on 415 patients, 5 folds each, plus the final test (results in EXPERIMENTS.md)

## After batch 3: more lung data (E11 first, then E10) (planned 2026-11-05)
Why: E9 showed more patients *of the same kind* add little (25% scored like 100%). What can help is *different*
data (other hospitals, scanners, tumour sizes). So first measure how our best model does on another hospital (E11),
then add data where it fails (E10).

| Dataset (public, TCIA) | What it has | Use | Check before use |
|---|---|---|---|
| NSCLC-Radiogenomics (Stanford / Palo Alto VA) | ~211 patients, ~144 with a primary-tumour mask (DICOM SEG, 1 class) | **E11 outside test** first; later half to training (E10) | counts and licence (listed CC BY 3.0) on the TCIA page |
| Medical Segmentation Decathlon, Task06 Lung | ~63 training CTs with tumour masks, already NIfTI | E10: add to training | may share patients with Radiogenomics: match before splitting; CC BY-SA 4.0 |
| NSCLC-Radiomics-Interobserver1 (Maastro) | 22 patients, 21 with GTVs from 5 oncologists each (RTSTRUCT + SEG) | **Evaluation only**: how well doctors agree = realistic ceiling; compare model vs each doctor | same hospital as our data: check those patients are not in our training folds |
| LIDC-IDRI | ~1,000 chest CTs, small nodules outlined by up to 4 radiologists | Optional (E10b): small-tumour practice | label means "nodule", not radiotherapy GTV: train as a separate run, never mixed blindly |

Preparation, so new data lines up with what we have (same steps as `prep/01`-`03`):
1. **Download** with `prep/00_download.py` (TCIA) or the MSD archive; one folder per dataset under `data/<dataset>/`.
2. **Inventory**: slices, spacing, scanner, label names; flag uneven spacing and missing tumour masks (as for Lung1).
3. **Convert** to the same NIfTI layout: CT in HU as `imagesTr/<id>_0000.nii.gz`, label 1 = tumour as `labelsTr/<id>.nii.gz`.
   New readers: DICOM SEG (Radiogenomics, Interobserver) via `highdicom` or `pydicom-seg`; MSD is NIfTI already (check HU and orientation).
4. **Same meaning of "tumour"**: primary tumour only (like GTV-1); drop node labels; note where the source drew differently.
5. **Remove duplicates** across datasets (same patient in two sets) by matching IDs and scan dates/sizes.
6. **QC picture** for every case, as for Lung1.
7. **Split**: keep our 60 locked Lung1 test patients unchanged; new training data only goes into the training folds;
   an outside-test dataset stays wholly separate and is used once.
8. **Spacing**: keep native spacing like now (our model is built for 3 mm slices); flag scans with thin slices (~1 mm)
   and decide then whether to resample them to 3 mm.

## E10 now: more, different lung data (planned 2026-11-16)
Goal: does training on other hospitals' scans make the model better on new hospitals, without getting worse on Lung1?
- [x] **1. Get the data** (CPU; scripts built 2026-11-16: `prep/10_radiogenomics.py download`, `prep/11_msd_lung.py download`, run on the login node): NSCLC-Radiogenomics (TCIA, CT + DICOM SEG) with `00_download.py --collection`;
  MSD Task06 Lung (NIfTI archive). Check counts, licences, and patients shared between the two
- [x] **2. Prepare it** like Lung1 (job 3615830 done 2026-11-19: Radiogenomics 143 of 144 usable (RG-R01-119 left out: uneven slice gaps), 125 thin-slice; MSD 63 of 63, 55 thin-slice; 12 MSD scans were repeats of Radiogenomics patients and dropped; built 2026-11-16 and rehearsed on fake data: SEG and MSD read back exactly, repeats dropped, split rules checked; `jobs/e10_prep.sbatch` runs 10/11 convert + `12_combine.py`): new SEG reader (`highdicom`), MSD check of HU and orientation, primary tumour only,
  QC pictures, flag thin-slice scans; one combined nnU-Net dataset `Dataset002_LungMulti`
- [x] **3. Split** (done by `12_combine.py`: Dataset002 = 355 Lung1 + 71 Radiogenomics B + 51 MSD = 477; outside test A = 72; Lung1 test 60 untouched): Radiogenomics half A = **outside test** (locked, used once); half B + MSD = extra training.
  Lung1 folds and its 60 test patients stay exactly as they are; new cases only ever join the training side
- [x] **4. E11 first, the "before" number**: today's final recipe on outside test A, no retraining (E11 done 2026-11-21 (job 3616425, 72 outside patients, mostly small: 52 small / 15 medium / 5 large): **final recipe 0.670**, found 66/72, HD95 4.8 mm, but outlines **24% smaller** than these doctors draw; nnU-Net pair alone 0.670; our U-Net 0.519, 57/72, 37% too small (thin slices). Like-for-like before E10: ResEnc L 250 ep alone **0.672**, 65/72. The tool holds up at another hospital (Lung1 test 0.677); small tumours even better here (0.647 vs 0.581); job 3616425; `jobs/e11_outside.sbatch`, built 2026-11-19: also scores ResEnc L 250 ep alone + ours, the like-for-like "before" for step 5)
- [x] **5. E10, the "after" number** (done 2026-11-23: **0.741** on outside test A (job 3618138, 72 patients: small 0.734, medium 0.727, large 0.859), found 68/72, HD95 3.0 mm, volume -5.8% (before: 0.672, 65/72, outlines ~24% too small). Caveat: Radiogenomics B is the same hospital as outside A, so this shows more data from a hospital fixes that hospital; Anhui (v2) tests a truly new one; `e10_nnunet_prep` 3616426 cancelled: fresh planning picked 1.25 mm slices, so the prep now reuses Dataset001's ResEnc L plan and only the data changes; 3616436 failed (moved plans lack dataset.json, now copied in), resubmitted; prep 3617659 -> training 3617660_[0-4] (2026-11-21); all 5 folds done 2026-11-22 (~9 h 52 m each; fold val 0.670 / 0.633 / 0.624 / ? / ?, not comparable with v1 folds); `e10_outside` submitted as 3618138; `e10_outside` scores nnU-Net only; `e10_unet` DROPPED after E11 (0.519 outside): 125/143 + 55/63 new scans have thin slices (~1.25 mm) and our U-Net works at native spacing, decide after E11; then `e10_outside` once; built 2026-11-19): retrain nnU-Net ResEnc L (250 ep, 5 folds) + our U-Net on Lung1 + new data;
  score on Lung1 validation folds (vs 0.638 / 0.582) and once on outside test A (vs step 4)
- Lung1 test was already used for the final test, so it is NOT reused to choose anything here


Where we are: nnU-Net ResEnc L leads (0.638 on validation); our U-Net 0.579 at its best setting, 0.594 on fold 0 with
the even bigger block; on test our U-Net already ties the first nnU-Net (0.589 vs 0.591) and is better on small tumours.
- [x] **1. Strongest nnU-Net** (0.643, barely better than 250 epochs): ResEnc L trained 1000 epochs (its two best gains together), 5 folds
- [x] **2. Our best U-Net on all folds** (0.582, levelled off): even bigger block + 100,000 steps, folds 1-4, then pick its best prediction setting
- [x] **3. Team up** (0.659, the best so far): average the best nnU-Net with our U-Net (ours is better on small tumours); mix chosen on validation
- [x] **4. MedSAM2 (foundation model, box hint)** (doctor box 0.730, the best of all; our box 0.613): (a) box from the doctor's outline = best case; (b) box from our model = real case. Scored apart, as a doctor-guided tool
- [x] **5. E7, pre-trained vs from scratch** (pre-training +0.04, Swin still behind; dropped) (added, runs alongside): Swin UNETR starting from MONAI's weights
  learned on ~5,000 CTs vs the same Swin from scratch (`b4_swin_big_fold0`, 0.531), fold 0, 2 seeds; STU-Net later
- [x] **6. Team up again** done: 0.653, same mix wins (stable). **7. MedSAM2 with the team-up's box**: 0.638, worse than the team-up alone (0.687 on fold 0); MedSAM2 stays a doctor-guided tool
- [x] **Then one final test** with the winner (done 2026-11-18: average 0.677, nnU-Net alone 0.692, ours alone 0.599; details in EXPERIMENTS.md), on the 60 locked patients (`jobs/final_test.sbatch`, built 2026-11-16)
- Later: STU-Net (second E7 model), outside data (E11), look at the 3 large always-missed patients

Run side by side (no step waits for another, except where noted):
- GPU now: 6.1 ResEnc L 1000 epochs, 6.2 our U-Net folds 1-4, E7 Swin pre-trained (one-time weight download first)
- Build now, try on today's models: 6.3 averaging (ResEnc L 250 + nnU-Net 1000 + our U-Net), 6.4 MedSAM2 on validation
  patients (one-time install + weight download)
- Waits: 6.3 is re-run with the 6.1 / 6.2 models when they finish; the final test waits for everything
- One-time setup on BigBlue (public files only): E7 weights `~/tumor-ai/weights/model_swinvit.pt` (MONAI release 0.8.1);
  MedSAM2 in its OWN environment `~/tumor-ai/.venv-medsam2` (torch 2.5.1, code pinned to commit 332f30d, checkpoint
  `MedSAM2_latest.pt`), so the main `.venv` and every other job stay unchanged

## Pick the final model from any network, not only ours (added 2026-11-06)
Goal: the final tool is whichever model scores best on validation (then tested once), nnU-Net included. Our own U-Net
stays as the learning reference. Same patients, folds and locked test for every model; choose on validation only.
- [ ] **nnU-Net, stronger presets**: ResEnc M / L (`nnUNetPlannerResEncM/L`, the nnU-Net team's own 2024 recommendation), 5 folds
- [ ] **nnU-Net, full length**: 1000 epochs (its default; we ran 250)
- [ ] **nnU-Net, best combination**: 2D + 3D ensemble (`nnUNetv2_find_best_configuration`)
- [ ] **Other networks**: MedNeXt, SegResNet (MONAI), STU-Net (pre-trained, nnU-Net based)
- [ ] **Pre-trained on many CTs**: Swin UNETR self-supervised weights (E7), STU-Net, VISTA3D (check it has a lung tumour class)
- [ ] **Doctor-guided (box or click)**: MedSAM / SAM-Med3D / nnInteractive (E8); a separate use (semi-automatic), compare apart
- [ ] **Average the best two or three** (batch 4 starts this with our U-Net + nnU-Net)

## After a winner: upload, review, download (added 2026-11-06)
DICOM in, a doctor reviews the AI outline, a file the planning system opens comes out. Public DICOM only until
hospital and university approve; the model runs locally (never a cloud AI service); every outline is a research draft.
- [x] **Step 1, `predict_dicom.py`** (built 2026-11-15 as `prototype/engine.py`; tested on a sample, RTSTRUCT reads back exactly) (command line): DICOM CT folder -> winning model -> `RTSTRUCT.dcm` (via `rt-utils`,
  tied to that CT), plus `mask.nii.gz`, a few overview pictures and a small `summary.json` (tumour size, how sure)
- [x] **Step 2, small review page** (built 2026-11-15: `prototype/`, see its README; own canvas viewer instead of NiiVue, no internet needed; waits for the real models from BigBlue) (local, research): upload a zipped DICOM folder; view the CT slice by slice with the
  AI outline on top (NiiVue, reads DICOM in the browser); slider for the cut-off; accept / reject / note;
  download RTSTRUCT, mask and a one-page PDF. FastAPI endpoint + one React page, like the portal
- [ ] **Step 3, inside the portal** (needs approval): "Tumour outline" in the patient chart; pick the CT from PACS
  (`backend/pacs_gateway.py`) instead of uploading; reuse the DocAssist review pattern (AI draft -> doctor reviews ->
  save to chart, AI original kept, audit log); explain at role levels (`/api/explain-levels`); dose effect via
  `backend/radiation.py` (E13). The portal's file-upload analysis sends files to Gemini, so scans must NOT use that route
- Where it runs: our U-Net is small and runs on a normal CPU in about a minute per CT; nnU-Net (5 folds) on CPU is
  slower (minutes to tens of minutes); a GPU box at the hospital if needed

## Later: report learning and pelvis (added 2026-10-30, details in README section 6)
- [ ] Apply for Stanford AIMI data use agreement for Merlin Plus (pelvis/abdomen CT + reports)
- [ ] E14: report supervision (R-Super idea) on lung, using ReXGroundingCT / CT-RATE reports
- [ ] E15: pelvis model on Merlin Plus, Merlin-Cancer-Super as baseline

## Rules
- Only public data on HPC. Clinic data stays off it until the hospital and university both approve.
- Never run training on the login node.
- Every run uses `data/splits.json` and records its seed; the test patients are used once, at the very end.

## Model versions (decided 2026-11-21)
A version = fixed weights + recipe (mix, cut-off, piece rule) + the patients it was trained on, frozen read-only in
`~/tumor-ai/versions/<name>/` with a MANIFEST (sha256) by `jobs/freeze_version.sh`. Checkpoint rule, the same for every
version: nnU-Net `checkpoint_final`, our U-Net `best.pt` (best on its own validation patients); never picked on test patients.
- [x] **v1**: Lung1 only, the final-test recipe (0.677 test, 0.670 outside). Short paper + prototype. Frozen 2026-11-21 22:06 in `versions/v1` (25 files, sha256 MANIFEST)
- [x] **v1.1** (frozen 2026-11-23, versions/v1.1, 9 files, 5.2 GB): E10, nnU-Net ResEnc L 250 ep on Lung1 + Radiogenomics B + MSD (our U-Net not retrained). Freeze when the 5 folds finish (folds and outside test done 2026-11-23: outside A 0.741 vs v1's 0.672; ready to freeze)
- [ ] **v2**: Lung1 + E10 data + Anhui ASLS26 (~315 train, ~135 locked test). Decided 2026-11-22: **Cetuximab dropped**
  (dbGaP access too slow and PI-only); the notes below are kept for reference only. Steps 3-4 still apply to Anhui.
  **Built 2026-11-22, tested on fake data:** `prep/14_v2.py` locks 30% of usable Anhui (size-balanced, seed 42, ~134) as
  v2's test BEFORE training; ~313 join the training side of E10's folds (validation = same Lung1 patients); multi-piece
  training masks keep the largest piece (Lung1 = primary only); test masks untouched. Run order:
  - [ ] `sbatch jobs/v2_prep.sbatch` (CPU; job 3622372 done 2026-11-24 in 10 min: 790 cases preprocessed, spacing and patch match Dataset001)
  - [x] `sbatch --dependency=afterok:<prep> jobs/v2_nnunet.sbatch` (job 3622375, all 5 folds done 2026-11-24, ~9 h 50 m each; compare with v1 on the same validation patients: `model/compare_folds.py`)
  - [ ] `sbatch jobs/v2_test.sbatch` ONCE after all folds + anhui_v1: ResEnc L on v1 / E10 / v2 data + v1 recipe on the
    locked Anhui slice, and v2 on outside A
  1. Access (checked 2026-11-21): TCIA stopped hosting controlled data on 2025-07-08; requests now go through **dbGaP**
     (needs the trial's PHS number, on TCIA's Clinical Trials page), download via NCI CRDC + TCIA Data Retriever.
     Only a faculty-level PI may submit (students cannot): **Dr. Dasgupta submits, the student is added to the project**.
     No timeline stated; plan on weeks, not days. Data-use agreement (DUA) terms not yet read (licence PDF link moved):
     check sharing models / tool use / publication rules before requesting
  2. Check the RTSTRUCTs really hold a primary GTV and how they are named
  3. Before any training: lock a new test slice (whole sites if sites are identified; else a random 20%), used once
  4. Switching rule, fixed now: v2 replaces v1 only if, on the same validation patients, it is better beyond the 95% range
     AND not worse on Lung1 or on small tumours; then confirmed once on the new locked slice. Lung1 test and outside A are
     reported, never used to choose

## Outside test 2: Anhui Chest Hospital (planned 2026-11-22)
Science Data Bank doi 10.57760/sciencedb.29318, CC0, one hospital (Hefei, China), Siemens SOMATOM Definition AS+.
ASLS26: 449 stage III-IV, radiotherapy GTVs by 2+ radiation oncologists (consensus) = our kind of outline; 19.9 GB.
ESLS26: 730 stage I-II adenocarcinoma, diagnostic outlines by radiologists (not GTVs); 64.5 GB: small-tumour test later.
Zips are marked "not for bots": download in a browser, copy to `~/tumor-ai/data/anhui/`. The sheet has no histology per
patient, so the 74 small-cell cases cannot be separated (stated as a limitation).
- [x] 1. `jobs/anhui_prep.sbatch` (`prep/13_anhui.py`): unzip, convert, place each mask by header / index / head-feet flip
  (whichever looks like a lung tumour; unclear = left out), count mask pieces (lymph nodes?), QC pictures
  Job 3617790: 447/449 usable (315, 390: alignment unclear), all placed by header, tumour-likeness median 0.36;
  37 with >1 piece. 49 scored <0.15 but none scored clearly better flipped (mostly large tumours touching tissue).
- [ ] 2. Look at counts, pieces and QC pictures before scoring
- [x] 3. **Result 2026-11-24 (results/anhui_asls_v1.csv, 447 patients): v1 recipe 0.594**, found 368/447, HD95 18.9 mm, outlines 28% smaller than these doctors draw (small 0.524, n=58; medium 0.553, n=183; large 0.649, n=206); nnU-Net pair alone 0.549, 340/447; our U-Net alone 0.495, 341/447. A clear drop from Lung1 test 0.677 and outside A 0.670; the average helps more here (+0.045) than on Lung1. Breakdown (describing, not choosing): one-piece masks 0.601 (n=410, 71 missed) vs multi-piece 0.516 (n=37, 8 missed); tumour-likeness <0.15 0.411 (n=49, **19 missed**) vs >=0.15 0.616 (n=398, 60 missed): 11% of patients hold 24% of the misses, so some of those masks may sit off the tumour or the tumour touches other tissue. (submitted 2026-11-22, job 3617819; cancelled 2026-11-23 after 275/447 scored (~15 patients/h, it would likely have finished; the count was misread as 75); step 2 rerun split over 8 GPUs (job 3622368, all 8 parts done 2026-11-24, ~1 h 25 m each) with `jobs/anhui_v1_parts.sbatch`, joined by `model/merge_scores.py`, built 2026-11-23) `jobs/anhui_v1.sbatch`, ONCE: v1 unchanged + each model alone + four-level explanations. Nothing chosen here
- Later (v2): lock a test slice of ASLS26 before any training on the rest
