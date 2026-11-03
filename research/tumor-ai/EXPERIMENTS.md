# Experiments

- [x] **E0**: pipeline bug test, our U-Net on 1 patient. Dice 0.90
- [x] **E1-small**: nnU-Net, 50 patients, fold 0. Dice 0.547 (job 3516117, 1 h 03 min, `nnUNet_compile=f`)
- [x] **E3-small**: our U-Net, 50 patients, fold 0. Best Dice 0.300 (job 3516111, 1 h 32 min). Good on 4 of 9 patients (0.57 to 0.72), missed 5 (0.00). Re-scored with overlapping prediction + largest piece (job 3517030): 0.297, no gain; the misses are real misses
- [x] **E1**: nnU-Net, 415 usable patients, 5 folds (job 3517863, ~2 h 55 min per fold). Val Dice 0.581 / 0.501 / 0.474 / 0.611 / 0.469, mean 0.527
- [x] **Final test** (job 3519743, 60 locked patients, 5 folds averaged): nnU-Net Dice 0.591, found 47/60, volume -6.5%; our U-Net Dice 0.468, found 40/60, volume -39%. Small tumours (<20 cc): 0.449 vs 0.244. Our U-Net outlines too small and misses small tumours. Scores in `results/test_scores.csv` on BigBlue
- [ ] **E2**: 2D vs 3D (nnU-Net)
- [x] **E3**: our U-Net, 415 usable patients, 5 folds (job 3517862, ~4 h 48 min per fold). Best val Dice 0.450 / 0.430 / 0.388 / 0.473 / 0.317, mean 0.412
- [ ] **E4**: our U-Net + one change for small tumours
- [ ] **E5**: two-stage (find, then outline)
- [ ] **E6**: transformer (Swin UNETR)
- [ ] **E7**: pre-trained and fine-tuned vs from scratch
- [ ] **E8**: MedSAM with a box prompt
- [ ] **E9**: 25 / 50 / 100% of training patients
- [ ] **E10**: add Radiogenomics + Decathlon Lung
- [ ] **E11**: test on another dataset (outside test)
- [ ] **E12**: preparation settings (HU window, flip, block size)
- [ ] **E13**: do outline errors change the dose?
