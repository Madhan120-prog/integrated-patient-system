# Experiments

- [x] **E0**: pipeline bug test, our U-Net on 1 patient. Dice 0.90
- [x] **E1-small**: nnU-Net, 50 patients, fold 0. Dice 0.547 (job 3516117, 1 h 03 min, `nnUNet_compile=f`)
- [x] **E3-small**: our U-Net, 50 patients, fold 0. Best Dice 0.300 (job 3516111, 1 h 32 min). Good on 4 of 9 patients (0.57 to 0.72), missed 5 (0.00). Re-scored with overlapping prediction + largest piece (job 3517030): 0.297, no gain; the misses are real misses
- [x] **E1**: nnU-Net, 415 usable patients, 5 folds (job 3517863, ~2 h 55 min per fold). Val Dice 0.581 / 0.501 / 0.474 / 0.611 / 0.469, mean 0.527
- [x] **Final test** (job 3519743, 60 locked patients, 5 folds averaged): nnU-Net Dice 0.591, found 47/60, volume -6.5%; our U-Net Dice 0.468, found 40/60, volume -39%. Small tumours (<20 cc): 0.449 vs 0.244. Our U-Net outlines too small and misses small tumours. Scores in `results/test_scores.csv` on BigBlue

## Batch 1: independent experiments, fold 0, all submitted together (submitted 2026-11-02)
Each run changes ONE thing from E3 fold 0 (val Dice 0.450) or nnU-Net 3D fold 0 (0.581). Every run keeps its own
folder `runs/<name>/` (settings.json, log.csv, best.pt, summary.json) and refuses to overwrite one that exists.
One table of everything: `module load python/3.12.9/gcc.8.5.0 && cd ~/tumor-ai/model && ../.venv/bin/python collect.py` (saved to `results/all_runs.csv`).

- [x] `e4af_predict_fold0-4`: E4a cut-off 0.2/0.3/0.4/0.5 and E4f centre-weighted blocks, on the E3 models (no training). Job: 3544322_[0-4]. Folds 0-2 done; the plain_0.5 rows equal E3 exactly (check passed).
  Best: **plain cut-off 0.3**, +0.090 / +0.069 / +0.056 on folds 0 / 1 / 2 (mean 0.494 vs E3 0.423), size vs doctor
  from -46/-33/-44% to -10/-9/-3%. Centre-weighted at 0.5 also helps (+0.068 / +0.051 / +0.053) but with a lower
  cut-off it outlines too big (+15 to +25%). All 5 folds (mean val Dice): plain 0.5 = 0.412 (= E3, check passed), **plain 0.3 = 0.506 (+0.094)**,
  plain 0.4 = 0.480, gauss 0.5 = 0.476, plain 0.2 = 0.457. Chosen on validation: **cut-off 0.3**
- [x] `e4b_deepsup_fold0`: E4b deep supervision. Job: 3544323_0. **0.453 (+0.004)**, found 48/71, 4 h 54 min
- [x] `e4c_moreaug_fold0`: E4c + rotation, zoom, gamma. Job: 3544323_1. **0.445 (-0.004)**, found 51/71, 4 h 51 min
- [x] `e4d_zscore_fold0`: E4d nnU-Net brightness scaling. Job: 3544323_2. **0.464 (+0.014)**, found 51/71, 4 h 52 min
- [x] `e4e_bigger_fold0`: E4e 5 levels, up to 320 channels. Job: 3544323_3. **0.438 (-0.012)**, found 50/71, 4 h 58 min
- [x] `e6_swin_fold0`: E6 Swin UNETR. Job: 3544323_4. **0.517 (+0.067)**, found 52/71, 11 h 31 min
- [x] `e9_frac25_fold0`, `e9_frac50_fold0`: E9 25% / 50% of training patients (100% = E3). Job: 3544323 (tasks 5, 6). **25%: 0.448 (-0.002)**, found 46/71; **50%: 0.416 (-0.034)**, found 47/71
- [x] `e12_hu_wide_fold0`, `e12_flip_fold0`, `e12_patch_big_fold0`: E12 HU window, flip, bigger block. Job: 3544323 (tasks 7, 8, 9). **HU wide: 0.428 (-0.021)**, found 47/71; **flip: 0.451 (+0.002)**, found 50/71; bigger block still running (0.475 so far); bigger block final **0.545 (+0.095)**, found 52/71
- [x] `nnunet_2d_fold0`: E2 nnU-Net 2D. Job: 3544324. **0.563** vs 3D 0.581 (-0.019)

Reading so far (2026-11-03, 6 of 16 done): every finished change is within about +-0.03 of E3, and 25% of the
patients scores the same as 100% while 50% scores lower. So one run on one fold cannot separate these changes from
chance; the gap to nnU-Net is not about the amount of data. Swin was at 0.512 (+0.063) part way through.

## Batch 2: fold 0, queued behind batch 1 (submitted 2026-11-03)
- [x] `d1_trainfit_fold0`: D1 E3 fold 0 scored on its own 284 training patients (no training). Job: 3548626. On training patients: 0.552 at cut-off 0.3 (val 0.539). Train is about the same as val: the model cannot fit even what it has seen (under-fitting, not memorising)
- [x] `e3_seed7_fold0`: E3 repeated with another seed, to measure how much a score moves by chance. Job: 3548625_0. **0.496 (+0.046)** with nothing changed: a single fold-0 run moves about +-0.05 by chance
- [x] `e4g_sgd_fold0`: E4g nnU-Net optimizer (SGD, momentum 0.99, lr 0.01). Job: 3548625_1. **0.372 (-0.078)**, worse
- [x] `e4h_body_fold0`: E4h training blocks only from the box around the body. Job: 3548625_2. **0.452 (+0.002)**, no effect
- [x] `e4_combo_fold0`: brightness scaling + deep supervision + more augmentation + bigger block + body box. Job: 3548625_3. **0.538 (+0.089)**, found 52/71; the gain matches the bigger block alone
- [x] `e4_combo_sgd_fold0`: the combo + nnU-Net optimizer. Job: 3548625_4. **0.529 (+0.080)**
- [x] Final test again with the cut-off chosen on validation (all 5 e4af folds) -> `results/test_scores_cutoff.csv`. Job: 3548627 (waits for 3544322). **Our U-Net 0.533** (was 0.468), found 43/60 (was 40), size -9% (was -39%), HD95 10.2 mm; nnU-Net 0.591. Small 0.266 vs 0.449, medium **0.682 vs 0.639 (ours ahead)**, large 0.693 vs 0.720

Reading after batches 1-2 (2026-11-05): with cut-off 0.3 our U-Net reaches 0.533 on test (90% of nnU-Net) and beats
it on medium tumours; the whole remaining gap is small tumours. Chance alone moves a fold-0 score by about +-0.05, so only
three changes stand out: bigger block (+0.095), the combo (+0.089, which is the bigger block) and Swin (+0.067). The model
under-fits (train = val), so it needs more context or capacity, not more data or regularisation. Next: bigger block +
cut-off 0.3 on all 5 folds, then the final test; then work on small tumours.

## Batch 3: lock in the bigger block, then small tumours (built and submitted 2026-11-05)
Every fold-0 idea runs with 2 seeds (42, 7). Baseline = bigger block, fold 0: `e12_patch_big_fold0` (0.545) + `b3_big_seed7_fold0`.
- [x] `b3_big_fold1-4`: bigger block on folds 1-4 (fold 0 = `e12_patch_big_fold0`). Job: 3556775_[1-4], ~7 h each. **0.449 / 0.467 / 0.530 / 0.424**; with fold 0 (0.545) mean **0.483 vs E3 0.412 (+0.071), better on every fold** (+0.019 to +0.107). nnU-Net mean 0.527
- [x] `b3_predict_fold0-4`: cut-off 0.2-0.5, centre-weighting, largest vs most confident piece, on validation. Job: 3556776_[0-4] (waits for 3556775)
- [x] Final test, bigger block, 5 folds, setting chosen on validation -> `results/test_scores_b3.csv`. Job: 3556777. Setting chosen on validation: centre-weighted, cut-off 0.2, most confident piece. **Our U-Net 0.589 vs nnU-Net (E1) 0.591: tied.** Found 48/60 vs 47/60, size +6.8% vs -6.5%, HD95 10.2 vs 9.7 mm. Small 0.488 vs 0.449 and medium 0.673 vs 0.639 (ours ahead), large 0.610 vs 0.720 (nnU-Net ahead)
- [x] `b3_big_seed7_fold0`: baseline repeat (seed 7). Job: 3556778_0. **0.511** (seed 42: 0.545), baseline mean **0.528**
- [x] `b3_huge_fold0` + `_seed7`: even bigger block 80x224x224. Job: 3556778 (tasks 1, 2), ~10 h. **0.558 / 0.548, mean 0.553 (+0.025)**: both seeds above both baseline seeds, small gain
- [x] `b3_long_fold0` + `_seed7`: 100,000 steps. Job: 3556778 (tasks 3, 4), ~13 h. **0.556 / 0.577, mean 0.567 (+0.039)**: best idea, fits under-fitting
- [x] `b3_fg50_fold0` + `_seed7`: half the blocks on tumour. Job: 3556778 (tasks 5, 6). **0.536 / 0.530, mean 0.533 (+0.005)**: no effect
- [x] `b3_tversky_fold0` + `_seed7`: Tversky loss (misses cost more). Job: 3556778 (tasks 7, 8). **0.526 / 0.493, mean 0.509 (-0.019)**: no help
- [x] Always-missed test patients (neither model, Dice <= 0.1, from `results/test_scores_cutoff.csv`): 11 of 60.
  LUNG1-063, 075, 076, 087, 098, 135, 156, 303, 311, 377, 404. Both models score 0.0 on all 11.
  8 are small (0.8-12.4 cc): 063, 076, 087, 098, 135, 156, 311, 404. In 5 of these at least one model outlined something,
  but in the wrong place (size +60% to +7500%): it kept the wrong piece. 3 are large (075 88 cc, 303 158 cc, 377 464 cc) and
  both models find almost nothing: suspicious, check the scan and the doctor's outline lines up (look at them before trusting)
- Not in batch 3: averaging our U-Net with nnU-Net needs nnU-Net's probability outputs (`--save_probabilities`) on validation and test: batch 4.

## Batch 4: first two jobs, independent of batch 3 (built 2026-11-05)
- [x] `b4_nnunet_prob` (done, ~20 min per fold, 1 h 19 min test): nnU-Net prediction again with probabilities saved, folds 0-4 on their own validation patients + 5-fold test -> `data/full/prob_nnunet/` (no training). Job: 3556788_[0-5] (tasks 0-4 validation folds, 5 test)
- [x] `b4_swin_big_fold0`: Swin UNETR + bigger block 64x192x192 (our two best single changes together). Job: 3556789, 14 h 36 min. **0.531**, no gain over the bigger block alone (0.545 / 0.511) at twice the time: drop Swin
- [x] `b4_resenc_prep` + `b4_resenc` folds 0-4 (~9 h 50 min each: **0.677 / 0.659 / 0.619 / 0.692 / 0.543, mean 0.638 vs E1 0.527, +0.111, better on every fold; best model so far**): nnU-Net ResEnc L preset, 250 epochs like E1 (network is the only change). Job: prep 3556864, training 3556865_[0-4] (waits for prep)
- [x] `b4_nnunet_1000ep` folds 0-4 (~10 h 40 min each: **0.650 / 0.647 / 0.580 / 0.673 / 0.534, mean 0.616 vs E1 0.527, +0.089**, better on every fold): nnU-Net 3d_fullres at its normal 1000 epochs (E1 used 250). Job: 3556866_[0-4]
- Not yet: nnU-Net 2D + 3D combined needs validation probabilities from the 2D run (re-run its validation with `--npz`)
- Next in batch 4, after batch 3: average our U-Net with nnU-Net (chosen on validation, then the test)

Reading after batch 3 (2026-11-07): the bigger block is real (better on all 5 folds, mean 0.483 vs 0.412). Of the new
ideas only training longer clearly helps, for both models: our U-Net +0.039 (two seeds), nnU-Net 1000 epochs +0.069 on
fold 0. Tumour share and Tversky do nothing. Both models were stopped too early. Fold-0 gap now: nnU-Net 1000 ep 0.650 vs our best 0.567.

## Batch 5: train longer (built 2026-11-07)
- [x] `b5_long_fold1-4` (~13 h each: **0.478 / 0.488 / 0.563 / 0.456**; with fold 0 (0.556) mean **0.508 vs bigger block 0.483, +0.025, better on every fold**): bigger block + 100,000 steps on folds 1-4 (fold 0 = `b3_long_fold0`): our U-Net's best recipe on 5 folds. Job: 3561162_[1-4]
- [x] `b5_predict_fold0-4` (best on validation: **centre-weighted, cut-off 0.3, most confident piece, mean 0.579** vs 0.508 at plain 0.5; all 4 best settings use the most confident piece): cut-off, centre-weighting, piece choice on validation for that recipe (no test yet). Job: 3561163_[0-4] (waits for 3561162)
- [x] `b5_vlong_fold0` + `_seed7` (~25 h each: **0.541 / 0.544, mean 0.542 vs 100k 0.567, -0.025**: longer than 100k does not help): bigger block, 200,000 steps (does even longer keep helping?). Job: 3561164 (tasks 0, 1)
- [x] `b5_huge_long_fold0` + `_seed7` (~20 h each: **0.573 / 0.616, mean 0.594 vs 100k 0.567, +0.027**; the two gains add up; our best recipe): even bigger block 80x224x224 + 100,000 steps (do the two gains add up?). Job: 3561164 (tasks 2, 3)
- Final test only once, for the final recipe (our best, nnU-Net best, or their average).

Reading after batches 3-5 (2026-11-10): our bigger-block U-Net now ties the first nnU-Net on test (0.589 vs 0.591)
and beats it on small and medium tumours. But nnU-Net improved more: on 5-fold validation ResEnc L 0.638 and 1000 epochs
0.616, against E1 0.527 and our best 0.508 (cut-off 0.5; the cut-off choice adds a few points for ours). Swin adds nothing.
Leader: nnU-Net ResEnc L. Next: ResEnc L at 1000 epochs, then average the best models, then one final test.

## Batch 6: next 4 experiments (planned 2026-11-10, not built yet; plain-words version in `plan.md`)
- [ ] **6.1** Strongest nnU-Net: ResEnc L at 1000 epochs, 5 folds (E1 line: combines `b4_resenc` + `b4_nnunet_1000ep`). `batch6_resenc_1000ep.sbatch`. Job:
- [ ] **6.2** Our best U-Net on all folds: even bigger block 80x224x224 + 100,000 steps, folds 1-4, then the setting search (E12 line, fold 0 = `b5_huge_long_fold0`). `batch6_folds` + `batch6_predict`. Job:
- [ ] **6.3** Team up: average the best nnU-Net with our U-Net, mix chosen on validation (the batch 4 "average" step). `ensemble.py`; first with today's models: probabilities `batch6_nnunet_prob` (ResEnc L, 1000 ep), then `batch6_avg` (our b5 U-Net). Job:
- [ ] **6.4** MedSAM2 with a box hint = **E8**; (a) box from the doctor's outline (best case), (b) box from our model's outline (real case, also **E5**: find, then outline). `medsam_box.py` + `batch6_medsam.sbatch`, fold 0 validation; separate `.venv-medsam2`. Job:
- [ ] **6.5** E7 pre-trained: Swin UNETR from MONAI's self-supervised weights (~5,000 CTs) vs Swin from scratch (`b4_swin_big_fold0`), fold 0, 2 seeds; runs alongside 6.1-6.4. `train.py --pretrained`, `batch6_e7.sbatch` (+ a from-scratch seed-7 run). Job:
- Then one final test with the winner

Later batches (need something first): E4d part 2 resampling (new data prep), E5, E7 and E8 (pre-trained weights), E10, E11, E13.

- [ ] **E2**: 2D vs 3D (nnU-Net)
- [x] **E3**: our U-Net, 415 usable patients, 5 folds (job 3517862, ~4 h 48 min per fold). Best val Dice 0.450 / 0.430 / 0.388 / 0.473 / 0.317, mean 0.412
- [ ] **E4**: our U-Net + one change for small tumours
- [ ] **E5**: two-stage (find, then outline)
- [ ] **E6**: transformer (Swin UNETR)
- [ ] **E7**: pre-trained and fine-tuned vs from scratch
- [ ] **E8**: MedSAM with a box prompt
- [x] **E9**: 25 / 50 / 100% of training patients (batch 1: 0.448 / 0.416 / 0.450, more data did not help then)
- [ ] **E10**: add Radiogenomics + Decathlon Lung (plan: `plan.md`, "After batch 3: more lung data")
- [ ] **E11**: test on another dataset (outside test): NSCLC-Radiogenomics, before E10 (plan in `plan.md`)
- [ ] **E12**: preparation settings (HU window, flip, block size)
- [ ] **E13**: do outline errors change the dose?
