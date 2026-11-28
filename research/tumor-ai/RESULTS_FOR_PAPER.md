# Tumor AI: all results

Read directly from the result files on BigBlue (`~/tumor-ai/results/`), 2026-11-27. Public data only.

**How to read the numbers**
- **Overlap** (Dice) runs from 0 to 1, where 1 is a perfect match with the doctor's outline. It is averaged over all patients, and a missed tumour counts as 0.
- **Found** means the AI outline touches the doctor's tumour.
- **Edge error** (HD95) is the median distance between the two outlines' edges, in mm. Lower is better.
- **Size** compares the AI outline's volume with the doctor's. It is a median, and minus means the AI drew it smaller.
- **Tumour size groups** are small (under 20 cc), medium (20–100 cc) and large (over 100 cc).
- **v1** is the model the system uses: 25% our U-Net plus 75% the nnU-Net pair (ResEnc L 250 ep + nnU-Net 1000 ep), cut-off 0.3, keeping the most confident piece.

---

## Table 1. The system's model (v1) at three hospitals, unchanged

| Test set | Patients | Overlap | Found | Edge error | Size |
|---|---|---|---|---|---|
| Lung1 locked test (Netherlands) | 60 | **0.677** | 52 / 60 | 6.9 mm | −0.1% |
| Outside A: NSCLC-Radiogenomics (US) | 72 | **0.670** | 66 / 72 | 4.8 mm | −24.7% |
| Outside B: Anhui Chest Hospital ASLS26 (China) | 447 | **0.594** | 368 / 447 | 18.9 mm | −28.3% |
| **Total** | **579** | | **486 / 579** | | |

## Table 2. Each part alone vs combined (overlap, found)

| Model | Lung1 test (60) | Outside A (72) | Outside B (447) |
|---|---|---|---|
| Our 3D U-Net | 0.599 · 48 | 0.519 · 57 | 0.495 · 341 |
| nnU-Net pair | **0.692** · 53 | **0.670** · 66 | 0.549 · 340 |
| **v1 (combined)** | 0.677 · 52 | **0.670** · 66 | **0.594** · 368 |

Combining helps most at the hardest hospital (+0.045 at B). On Lung1 the nnU-Net pair alone is 0.015 higher, which is within noise for 60 patients.

## Table 3. v1 by tumour size (overlap, found)

| Size | Lung1 test | Outside A | Outside B |
|---|---|---|---|
| Small (< 20 cc) | 0.581 · 17/22 | 0.647 · 46/52 | 0.524 · 43/58 |
| Medium (20–100 cc) | 0.768 · 22/22 | 0.695 · 15/15 | 0.553 · 142/183 |
| Large (> 100 cc) | 0.682 · 13/16 | 0.841 · 5/5 | 0.649 · 183/206 |

## Table 4. Training on more hospitals (same model type, ResEnc L; described only, nothing chosen)

| Trained on | Outside A (72) | Anhui locked slice (134) |
|---|---|---|
| Lung1 only | 0.672 · 65/72 · −23.5% | 0.422 · 79/134 · −48.0% |
| + 122 cases (E10 / v1.1; 71 from A's hospital) | **0.741** · 68/72 · −5.8% | 0.578 · 111/134 · −29.6% |
| + 313 Anhui training patients (v2) | 0.725 · 67/72 · −7.9% | **0.677** · 122/134 · −5.3% |
| v1 (reference) | 0.670 · 66/72 | 0.596 · 111/134 · −29.6% |

**Finding.** Training on a hospital's own outlines gives the biggest gain at that hospital:
- A rises from 0.672 to 0.741, with A's cases added.
- B rises from 0.596 to 0.677, with B's cases added, and the outlines stop being too small.

The gain does not carry over. v2 is lower at A (0.725 vs 0.741) and on the 355 Lung1 validation patients (0.623 vs v1's 0.638; 95% range −0.030 to −0.001). By the rule set beforehand, **v1 stays**.

## Table 5. Explanation levels (v1, cut-off 0.3)

| Check | Validation (71) | Locked test (60) |
|---|---|---|
| Texts with a number not in the fact sheet | 0 / 284 | 0 / 240 |
| Same side of the chest as the doctor's outline | 68/71 (96%) | 55/59 (93%) |
| Same part of the lung | 62/71 (87%) | 50/59 (85%) |
| Volume error, median | 10.0 cc (18.5%) | 5.9 cc (18.5%) |
| Longest-diameter error, median | 5 mm | 4 mm |
| Reading grade: patient / physician / physicist / AI | 3.7 / 6.4 / 6.6 / 6.3 | 3.7 / 6.4 / 6.6 / 6.6 |

## Table 6. Does the AI's stated confidence warn when the outline is poor? (new)

The physician and physicist levels state the mean AI confidence inside the outline and the share of the outline in the uncertain band (30–70%). Both track the real overlap:

| | Validation (71) | Locked test (59 found) |
|---|---|---|
| Rank correlation: confidence vs overlap | **0.78** | **0.66** |
| Rank correlation: uncertain band vs overlap | **−0.83** | **−0.70** |
| Overlap, least-confident quarter of patients | 0.368 (n=17) | 0.376 (n=14) |
| Overlap, other three quarters | 0.788 | 0.785 |
| Poor outlines (overlap < 0.5) in the least-confident quarter | 9 of 14 | 7 of 11 |

A low stated confidence flags most of the poor outlines. This is evidence that the uncertainty shown to doctors is useful, not decoration.

## Table 7. Where B's misses come from (described only; from the breakdown run of 2026-11-24, see plan.md)

| Group | Patients | Overlap | Missed |
|---|---|---|---|
| Doctor's outline in one piece | 410 | 0.601 | 71 |
| In several pieces (likely lymph nodes) | 37 | 0.516 | 8 |
| Tumour-likeness of the doctor's outline < 0.15 | 49 | 0.411 | 19 |
| Tumour-likeness ≥ 0.15 | 398 | 0.616 | 60 |

11% of patients account for 24% of the misses.

---

**Still to run:** `jobs/levels_outside.sbatch` repeats the Table 5 and Table 6 checks at outside A (72) and B (447).

**Not paper results:**
- `all_runs.csv` (988 rows) is the development log of every validation run.
- `test_scores.csv`, `test_scores_b3.csv` and `test_scores_cutoff.csv` are earlier versions, superseded by `test_scores_final.csv`.
