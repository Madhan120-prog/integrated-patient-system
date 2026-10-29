# Experiments

- [x] **E0**: pipeline bug test, our U-Net on 1 patient. Dice 0.90
- [x] **E1-small**: nnU-Net, 50 patients, fold 0. Dice 0.547 (job 3516117, 1 h 03 min, `nnUNet_compile=f`)
- [x] **E3-small**: our U-Net, 50 patients, fold 0. Best Dice 0.300 (job 3516111, 1 h 32 min). Good on 4 of 9 patients (0.57 to 0.72), missed 5 (0.00). Re-scored with overlapping prediction + largest piece (job 3517030): 0.297, no gain; the misses are real misses
- [ ] **E1**: nnU-Net, all 422 patients, 5 folds
- [ ] **E2**: 2D vs 3D (nnU-Net)
- [ ] **E3**: our U-Net, all 422 patients, 5 folds
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
