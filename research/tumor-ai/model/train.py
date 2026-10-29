"""Train our own 3D U-Net on one fold of the split. Short on purpose, so each step can be read.

    python model/train.py --data data/nnunet/Dataset001_LungGTV --splits data/splits.json --fold 0 --steps 20000

Writes runs/<name>/log.csv and best.pt (the weights with the best validation Dice).
"""
import argparse
import csv
import json
import random
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy import ndimage

from unet3d import UNet3D

HU_MIN, HU_MAX = -1000, 500     # air .. dense soft tissue; bone above 500 adds nothing for lung tumours


def load(data: Path, pid: str):
    img = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "imagesTr" / f"{pid}_0000.nii.gz"))).astype(np.int16)
    lab = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "labelsTr" / f"{pid}.nii.gz"))).astype(np.uint8)
    return img, lab


def normalise(hu: np.ndarray) -> np.ndarray:
    """Clip to the useful range, then scale to -1..1 so the network sees small, steady numbers."""
    return (np.clip(hu, HU_MIN, HU_MAX).astype(np.float32) - HU_MIN) / (HU_MAX - HU_MIN) * 2 - 1


def pad_to(a: np.ndarray, size, value):
    pads = [(0, max(0, s - d)) for s, d in zip(size, a.shape)]
    return np.pad(a, pads, constant_values=value)


def sample(img, lab, size, fg_prob, rng):
    """Cut one 3D block. A third of the time, centre it on a tumour voxel, else the model mostly sees lung."""
    img, lab = pad_to(img, size, HU_MIN), pad_to(lab, size, 0)
    if rng.random() < fg_prob and lab.any():
        centre = np.argwhere(lab)[rng.randrange(int(lab.sum()))]
        start = [int(np.clip(c - s // 2, 0, d - s)) for c, s, d in zip(centre, size, img.shape)]
    else:
        start = [rng.randrange(d - s + 1) for s, d in zip(size, img.shape)]
    sl = tuple(slice(b, b + s) for b, s in zip(start, size))
    return img[sl], lab[sl]


def augment(x: np.ndarray, rng) -> np.ndarray:
    """Brightness/contrast jitter and noise. No left-right flip: left and right lungs differ."""
    x = x * rng.uniform(0.9, 1.1) + rng.uniform(-0.1, 0.1)
    return x + np.random.default_rng(rng.randrange(2**31)).normal(0, 0.02, x.shape).astype(np.float32)


def dice_ce_loss(logits, target):
    """Cross-entropy teaches every voxel; soft Dice stops the tiny tumour from being ignored."""
    ce = F.cross_entropy(logits, target)
    p = logits.softmax(1)[:, 1]
    t = (target == 1).float()
    dice = (2 * (p * t).sum() + 1) / (p.sum() + t.sum() + 1)
    return ce + (1 - dice)


@torch.no_grad()
def predict(net, img, size, device):
    """Cover the whole scan with blocks that overlap by half, average the tumour probability where they
    overlap, then keep only the largest connected tumour piece (we outline one primary tumour, GTV-1).
    ponytail: plain average; nnU-Net weights block centres more (Gaussian), try it if edges still hurt."""
    shape = img.shape
    x = pad_to(normalise(img), size, -1)
    prob = np.zeros(x.shape, np.float32)
    count = np.zeros(x.shape, np.float32)
    starts = []
    for d, s in zip(x.shape, size):
        st = list(range(0, d - s + 1, s // 2))
        starts.append(st if st[-1] == d - s else st + [d - s])
    for z in starts[0]:
        for y in starts[1]:
            for xx in starts[2]:
                sl = (slice(z, z + size[0]), slice(y, y + size[1]), slice(xx, xx + size[2]))
                block = torch.from_numpy(x[sl][None, None].copy()).to(device)
                prob[sl] += net(block).softmax(1)[0, 1].cpu().numpy()
                count[sl] += 1
    mask = prob / count > 0.5
    pieces, n = ndimage.label(mask)
    if n > 1:
        mask = pieces == 1 + int(np.argmax(ndimage.sum(mask, pieces, range(1, n + 1))))
    return mask[:shape[0], :shape[1], :shape[2]].astype(np.uint8)


def dice(pred, gt):
    inter = np.logical_and(pred, gt).sum()
    return 2 * inter / (pred.sum() + gt.sum()) if pred.sum() + gt.sum() else 1.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--splits", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--steps", type=int, default=20000)
    ap.add_argument("--val-every", type=int, default=500)
    ap.add_argument("--patch", type=int, nargs=3, default=[32, 128, 128])
    ap.add_argument("--batch", type=int, default=2)
    ap.add_argument("--base", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--name", default=None)
    ap.add_argument("--eval-only", action="store_true", help="score runs/<name>/best.pt on the val patients, no training")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    fold = json.load(open(a.splits))["folds"][a.fold]
    data = Path(a.data)
    # ponytail: all training scans held in RAM as int16 (~30 MB each); switch to memory-mapped files past ~500 scans.
    train = [load(data, p) for p in fold["train"]]
    val = {p: load(data, p) for p in fold["val"]}

    if a.eval_only:
        ck = torch.load(Path("runs") / a.name / "best.pt", map_location=device)
        net = UNet3D(base=ck["args"]["base"]).to(device)
        net.load_state_dict(ck["model"])
        net.eval()
        scores = {p: round(float(dice(predict(net, img, ck["args"]["patch"], device), lab)), 3) for p, (img, lab) in val.items()}
        print(f"{a.name} (step {ck['step']}): val Dice {np.mean(list(scores.values())):.3f}  {scores}")
        return

    net = UNet3D(base=a.base).to(device)
    opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.PolynomialLR(opt, total_iters=a.steps, power=0.9)
    run = Path("runs") / (a.name or f"unet3d_fold{a.fold}")
    run.mkdir(parents=True, exist_ok=True)
    log = csv.writer(open(run / "log.csv", "w", newline=""))
    log.writerow(["step", "loss", "val_dice", "seconds"])
    best, t0, losses = -1.0, time.time(), []

    for step in range(1, a.steps + 1):
        xs, ys = zip(*(sample(*rng.choice(train), a.patch, 1 / 3, rng) for _ in range(a.batch)))
        x = torch.from_numpy(np.stack([augment(normalise(v), rng) for v in xs])[:, None]).to(device)
        y = torch.from_numpy(np.stack(ys).astype(np.int64)).to(device)
        net.train()
        loss = dice_ce_loss(net(x), y)
        opt.zero_grad()
        loss.backward()
        opt.step()
        sched.step()
        losses.append(loss.item())

        if step % a.val_every == 0 or step == a.steps:
            net.eval()
            scores = {p: dice(predict(net, img, a.patch, device), lab) for p, (img, lab) in val.items()}
            mean = float(np.mean(list(scores.values())))
            log.writerow([step, round(float(np.mean(losses)), 4), round(mean, 4), int(time.time() - t0)])
            print(f"step {step}: loss {np.mean(losses):.3f}  val Dice {mean:.3f}  {scores}")
            losses = []
            if mean > best:
                best = mean
                torch.save({"model": net.state_dict(), "args": vars(a), "step": step, "val_dice": mean}, run / "best.pt")
    print(f"best val Dice {best:.3f} -> {run / 'best.pt'}")


if __name__ == "__main__":
    main()
