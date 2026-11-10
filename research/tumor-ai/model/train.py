"""Train our own 3D U-Net on one fold of the split. Short on purpose, so each step can be read.

    python model/train.py --data data/nnunet/Dataset001_LungGTV --splits data/splits.json --fold 0 --steps 20000

Every run lives in its own folder, runs/<name>/, and an existing folder is never written over:
    settings.json  every setting, the job number, start time and a fingerprint of the code
    log.csv        loss and validation Dice at each check
    best.pt        the weights with the best validation Dice
    summary.json   the result, written when the run finishes (model/collect.py reads these)

Prediction-only experiments (no training) reuse a finished run's weights:
    python model/train.py --eval-only --from full_e3_fold0 --name e4af_predict_fold0 --cutoffs 0.3 0.4 0.5 --gauss ...
"""
import argparse
import csv
import hashlib
import inspect
import json
import math
import os
import random
import socket
import sys
import time
from pathlib import Path

import numpy as np
import SimpleITK as sitk
import torch
import torch.nn.functional as F
from scipy import ndimage

from unet3d import UNet3D

HU_MIN, HU_MAX = -1000, 500     # air .. dense soft tissue; bone above 500 adds nothing for lung tumours
HERE = Path(__file__).resolve().parent


def window_norm(lo=HU_MIN, hi=HU_MAX):
    """Clip to lo..hi and map it onto -1..1. Every brightness scaling here is (clip(hu, lo, hi) - mean) / std."""
    return {"lo": lo, "hi": hi, "mean": (lo + hi) / 2, "std": (hi - lo) / 2}


def zscore_norm(train):
    """nnU-Net style: clip to the 0.5-99.5 percentile of HU inside tumours, then mean 0, spread 1."""
    rng = np.random.default_rng(0)
    vals = np.concatenate([rng.choice(img[lab > 0], min(20000, int((lab > 0).sum()))) for img, lab in train if lab.any()])
    lo, hi = np.percentile(vals, [0.5, 99.5])
    v = np.clip(vals, lo, hi)
    return {"lo": float(lo), "hi": float(hi), "mean": float(v.mean()), "std": float(v.std())}


def load(data: Path, pid: str):
    img = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "imagesTr" / f"{pid}_0000.nii.gz"))).astype(np.int16)
    lab = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "labelsTr" / f"{pid}.nii.gz"))).astype(np.uint8)
    return img, lab


def crop_body(img, lab, margin=10):
    """--crop-body: cut the scan down to the box around the body (HU > -500) plus a margin, so random
    training blocks land on the patient instead of the air and table around them."""
    body = img > -500
    sl = []
    for ax in range(3):
        nz = np.flatnonzero(body.any(axis=tuple(i for i in range(3) if i != ax)))
        sl.append(slice(max(int(nz[0]) - margin, 0), min(int(nz[-1]) + margin + 1, img.shape[ax])) if nz.size else slice(None))
    sl = tuple(sl)
    return (img[sl], lab[sl]) if lab[sl].sum() == lab.sum() else (img, lab)   # never cut off tumour


def normalise(hu: np.ndarray, norm=None) -> np.ndarray:
    """Clip to the useful range, then scale so the network sees small, steady numbers."""
    n = norm or window_norm()
    return ((np.clip(hu, n["lo"], n["hi"]).astype(np.float32) - n["mean"]) / n["std"]).astype(np.float32)


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
    """Brightness/contrast jitter and noise. No left-right flip unless --flip: left and right lungs differ."""
    x = x * rng.uniform(0.9, 1.1) + rng.uniform(-0.1, 0.1)
    return x + np.random.default_rng(rng.randrange(2**31)).normal(0, 0.02, x.shape).astype(np.float32)


def more_augment(x, y, rng, p=0.3):
    """--aug more (nnU-Net style), on the GPU: in-plane rotation +-15 deg and zoom 0.85-1.15 for scan and mask
    together, then a gamma change of the scan. Each happens to a block with probability p."""
    n = x.shape[0]
    ang = [math.radians(rng.uniform(-15, 15)) if rng.random() < p else 0.0 for _ in range(n)]
    zoom = [rng.uniform(0.85, 1.15) if rng.random() < p else 1.0 for _ in range(n)]
    theta = torch.zeros(n, 3, 4, device=x.device)
    for i, (a, s) in enumerate(zip(ang, zoom)):        # rows act on (x, y, z); z (between slices) is left alone
        theta[i, 0, 0], theta[i, 0, 1] = math.cos(a) / s, -math.sin(a) / s
        theta[i, 1, 0], theta[i, 1, 1] = math.sin(a) / s, math.cos(a) / s
        theta[i, 2, 2] = 1.0
    grid = F.affine_grid(theta, list(x.shape), align_corners=False)
    x = F.grid_sample(x, grid, mode="bilinear", padding_mode="border", align_corners=False)
    y = F.grid_sample(y[:, None].float(), grid, mode="nearest", align_corners=False)[:, 0].long()
    for i in range(n):
        if rng.random() < p:
            lo, hi = x[i].min(), x[i].max()
            x[i] = ((x[i] - lo) / (hi - lo + 1e-8)) ** rng.uniform(0.7, 1.5) * (hi - lo) + lo
    return x, y


def dice_ce_loss(logits, target, ab=(0.5, 0.5)):
    """Cross-entropy teaches every voxel; soft Dice stops the tiny tumour from being ignored.
    ab = (weight of false alarms, weight of misses). (0.5, 0.5) is plain Dice; (0.3, 0.7) is the
    Tversky loss, which punishes missed tumour more than extra outline."""
    ce = F.cross_entropy(logits, target)
    p = logits.softmax(1)[:, 1]
    t = (target == 1).float()
    tp, fp, fn = (p * t).sum(), (p * (1 - t)).sum(), ((1 - p) * t).sum()
    overlap = (tp + 0.5) / (tp + ab[0] * fp + ab[1] * fn + 0.5)
    return ce + (1 - overlap)


def loss_fn(out, y, ab=(0.5, 0.5)):
    """One output: Dice+CE. Deep supervision (a list): the same loss at each size, halving the weight per level."""
    if not isinstance(out, list):
        return dice_ce_loss(out, y, ab)
    w = [0.5 ** i for i in range(len(out))]
    ys = [y if o.shape[2:] == y.shape[1:] else F.interpolate(y[:, None].float(), size=o.shape[2:], mode="nearest")[:, 0].long()
          for o in out]
    return sum(wi * dice_ce_loss(o, yi, ab) for wi, o, yi in zip(w, out, ys)) / sum(w)


def build(args: dict):
    """The network a run's settings describe. Older runs lack the newer keys, so each has a default."""
    if args.get("arch", "unet") == "swin":
        from monai.networks.nets import SwinUNETR      # block sizes must divide by 32
        kw = {"img_size": tuple(args["patch"])} if "img_size" in inspect.signature(SwinUNETR).parameters else {}
        return SwinUNETR(in_channels=1, out_channels=2, feature_size=48, **kw)
    strides = ((1, 2, 2),) + ((2, 2, 2),) * (args.get("levels", 4) - 2)
    return UNet3D(base=args["base"], strides=strides, deep_sup=args.get("deep_sup", False))


def gaussian_map(size):
    """Weight for one block: 1 at the centre, falling off towards the edges (nnU-Net uses sigma = size/8)."""
    g = [np.exp(-0.5 * ((np.arange(s) - (s - 1) / 2) / (s / 8)) ** 2) for s in size]
    w = g[0][:, None, None] * g[1][None, :, None] * g[2][None, None, :]
    return np.clip(w / w.max(), 1e-3, None).astype(np.float32)


@torch.no_grad()
def predict_prob(net, img, size, device, norm=None, gauss=False):
    """Tumour probability for the whole scan: blocks that overlap by half, averaged where they overlap.
    gauss=True weights each block's centre more than its edges, as nnU-Net does."""
    shape = img.shape
    x = normalise(pad_to(img, size, HU_MIN), norm)
    w = gaussian_map(size) if gauss else np.ones(size, np.float32)
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
                prob[sl] += net(block).softmax(1)[0, 1].cpu().numpy() * w
                count[sl] += w
    return (prob / count)[:shape[0], :shape[1], :shape[2]]


def confident_piece(mask, prob):
    """Keep the connected piece the model is most sure of (highest probability inside it), not the biggest,
    so a large false alarm cannot push out a small real tumour."""
    pieces, n = ndimage.label(mask)
    if n > 1:
        mask = pieces == 1 + int(np.argmax(ndimage.maximum(prob, pieces, range(1, n + 1))))
    return mask.astype(np.uint8)


def one_piece(prob, cutoff, how="largest"):
    m = prob > cutoff
    return confident_piece(m, prob) if how == "confident" else largest_piece(m)


def largest_piece(mask):
    """Keep only the largest connected tumour piece (we outline one primary tumour, GTV-1)."""
    pieces, n = ndimage.label(mask)
    if n > 1:
        mask = pieces == 1 + int(np.argmax(ndimage.sum(mask, pieces, range(1, n + 1))))
    return mask.astype(np.uint8)


def predict(net, img, size, device, norm=None, cutoff=0.5, gauss=False):
    return largest_piece(predict_prob(net, img, size, device, norm, gauss) > cutoff)


def dice(pred, gt):
    inter = np.logical_and(pred, gt).sum()
    return 2 * inter / (pred.sum() + gt.sum()) if pred.sum() + gt.sum() else 1.0


def new_run_dir(name):
    """runs/<name>/, refusing to touch a folder that already holds anything: no result is ever overwritten."""
    run = HERE / "runs" / name
    if run.exists() and any(run.iterdir()):
        sys.exit(f"runs/{name} already exists, so nothing was run (results are never overwritten). Use a new --name.")
    run.mkdir(parents=True, exist_ok=True)
    return run


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")


def code_fingerprint():
    return {f: hashlib.sha256((HERE / f).read_bytes()).hexdigest()[:12] for f in ("train.py", "unet3d.py")}


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
    # experiment switches; the defaults reproduce E3 exactly
    ap.add_argument("--arch", choices=["unet", "swin"], default="unet", help="E6: swin = Swin UNETR (MONAI)")
    ap.add_argument("--levels", type=int, default=4, help="E4e: U-Net levels (4 = E3)")
    ap.add_argument("--deep-sup", action="store_true", help="E4b: deep supervision")
    ap.add_argument("--aug", choices=["basic", "more"], default="basic", help="E4c: more = + rotation, zoom, gamma")
    ap.add_argument("--norm", choices=["window", "zscore"], default="window", help="E4d: zscore = nnU-Net brightness scaling")
    ap.add_argument("--hu", type=float, nargs=2, default=[HU_MIN, HU_MAX], help="E12: HU window for --norm window")
    ap.add_argument("--flip", action="store_true", help="E12: random left-right flip")
    ap.add_argument("--frac", type=float, default=1.0, help="E9: share of the fold's training patients to use")
    ap.add_argument("--opt", choices=["adamw", "sgd"], default="adamw", help="E4g: sgd = nnU-Net's optimizer (use --lr 0.01)")
    ap.add_argument("--crop-body", action="store_true", help="E4h: training blocks only from the box around the body")
    ap.add_argument("--fg", type=float, default=1 / 3, help="share of training blocks centred on tumour (E3: 1/3)")
    ap.add_argument("--loss", choices=["dice", "tversky"], default="dice", help="tversky = misses cost more than extra outline")
    ap.add_argument("--pretrained", default=None, help="E7: start Swin from weights learned on other CTs (MONAI model_swinvit.pt)")
    ap.add_argument("--exp", default="", help="experiment id for the record, e.g. E4b")
    ap.add_argument("--change", default="", help="what differs from the baseline, in words, for the record")
    # prediction-only experiments
    ap.add_argument("--eval-only", action="store_true", help="score a finished run's best.pt on its val patients")
    ap.add_argument("--from", dest="from_run", default=None, help="eval-only: the finished run to score")
    ap.add_argument("--cutoffs", type=float, nargs="+", default=[0.5], help="eval-only: tumour cut-offs to try")
    ap.add_argument("--gauss", action="store_true", help="eval-only: also try centre-weighted blocks")
    ap.add_argument("--pieces", nargs="+", choices=["largest", "confident"], default=["largest"],
                    help="eval-only: which connected piece to keep")
    ap.add_argument("--on", choices=["val", "train"], default="val", help="eval-only: score the run's val or its training patients")
    a = ap.parse_args()

    rng = random.Random(a.seed)
    torch.manual_seed(a.seed)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    record = {"name": a.name, "exp": a.exp, "change": a.change, "job": os.environ.get("SLURM_JOB_ID"),
              "array_job": os.environ.get("SLURM_ARRAY_JOB_ID"), "array_task": os.environ.get("SLURM_ARRAY_TASK_ID"),
              "host": socket.gethostname(), "started": time.strftime("%Y-%m-%d %H:%M:%S"), "code": code_fingerprint()}
    data = Path(a.data)

    if a.eval_only:
        src = a.from_run or a.name
        ck = torch.load(HERE / "runs" / src / "best.pt", map_location=device)
        fold = json.load(open(a.splits))["folds"][ck["args"]["fold"]]
        run = new_run_dir(a.name) if a.from_run else None
        if run:
            write_json(run / "settings.json", {**record, "from": src, "fold": ck["args"]["fold"], "scored_on": a.on, "args": vars(a)})
        net = build(ck["args"]).to(device).eval()
        net.load_state_dict(ck["model"])
        variants = [("plain", False)] + ([("gauss", True)] if a.gauss else [])
        name = lambda v, c, h: f"{v}_{c}" + ("" if h == "largest" else f"_{h}")
        per = {name(v, c, h): {} for v, _ in variants for c in a.cutoffs for h in a.pieces}
        for p in fold[a.on]:
            img, lab = load(data, p)
            for v, g in variants:
                prob = predict_prob(net, img, ck["args"]["patch"], device, ck.get("norm"), g)
                for c, h in [(c, h) for c in a.cutoffs for h in a.pieces]:
                    m = one_piece(prob, c, h)
                    per[name(v, c, h)][p] = {"dice": round(float(dice(m, lab)), 4),
                                         "vol_diff_pct": round(100 * (int(m.sum()) - int(lab.sum())) / int(lab.sum()), 1)}
        rows = [{"variant": k, "val_dice": round(float(np.mean([r["dice"] for r in d.values()])), 4),
                 "found": sum(r["dice"] > 0.1 for r in d.values()), "n_val": len(d),
                 "median_vol_diff_pct": float(np.median([r["vol_diff_pct"] for r in d.values()]))} for k, d in per.items()]
        for r in rows:
            print(f"{src} {r['variant']:<10} val Dice {r['val_dice']:.3f}  found {r['found']}/{r['n_val']}  "
                  f"size vs doctor {r['median_vol_diff_pct']:+.1f}%")
        if run:
            write_json(run / "summary.json", {**record, "from": src, "fold": ck["args"]["fold"], "scored_on": a.on, "rows": rows,
                                              "per_patient": per, "finished": time.strftime("%Y-%m-%d %H:%M:%S")})
        return

    run = new_run_dir(a.name or f"unet3d_fold{a.fold}")
    fold = json.load(open(a.splits))["folds"][a.fold]
    train_ids = fold["train"] if a.frac >= 1 else random.Random(a.seed).sample(fold["train"], round(len(fold["train"]) * a.frac))
    # ponytail: all training scans held in RAM as int16 (~30 MB each); switch to memory-mapped files past ~500 scans.
    train = [load(data, p) for p in train_ids]
    if a.crop_body:
        train = [crop_body(img, lab) for img, lab in train]
    val = {p: load(data, p) for p in fold["val"]}
    norm = zscore_norm(train) if a.norm == "zscore" else window_norm(*a.hu)
    pre = {"pretrained_sha256": hashlib.sha256(Path(a.pretrained).read_bytes()).hexdigest()[:12]} if a.pretrained else {}
    write_json(run / "settings.json", {**record, **pre, "fold": a.fold, "args": vars(a), "norm": norm,
                                       "train_patients": train_ids, "val_patients": fold["val"]})

    net = build(vars(a))
    if a.pretrained:        # E7: the Swin encoder starts from self-supervised weights; the decoder starts fresh
        assert a.arch == "swin", "--pretrained needs --arch swin"
        net.load_from(torch.load(a.pretrained, map_location="cpu", weights_only=False))
    net = net.to(device)
    print(f"{run.name}: {a.exp} {a.change} | {sum(p.numel() for p in net.parameters()) / 1e6:.2f} M weights, "
          f"{len(train)} training / {len(val)} validation patients", flush=True)
    if a.opt == "sgd":      # nnU-Net: SGD, Nesterov momentum 0.99, weight decay 3e-5, gradients clipped at 12
        opt = torch.optim.SGD(net.parameters(), lr=a.lr, momentum=0.99, nesterov=True, weight_decay=3e-5)
    else:
        opt = torch.optim.AdamW(net.parameters(), lr=a.lr, weight_decay=1e-4)
    sched = torch.optim.lr_scheduler.PolynomialLR(opt, total_iters=a.steps, power=0.9)
    log_file = open(run / "log.csv", "w", newline="")
    log = csv.writer(log_file)
    log.writerow(["step", "loss", "val_dice", "seconds"])
    best, best_step, best_scores, t0, losses = -1.0, 0, {}, time.time(), []

    for step in range(1, a.steps + 1):
        xs, ys = [], []
        for _ in range(a.batch):
            xi, yi = sample(*rng.choice(train), a.patch, a.fg, rng)
            if a.flip and rng.random() < 0.5:
                xi, yi = xi[..., ::-1], yi[..., ::-1]
            xs.append(augment(normalise(xi, norm), rng))
            ys.append(yi)
        x = torch.from_numpy(np.stack(xs)[:, None].copy()).to(device)
        y = torch.from_numpy(np.stack(ys).astype(np.int64)).to(device)
        if a.aug == "more":
            x, y = more_augment(x, y, rng)
        net.train()
        loss = loss_fn(net(x), y, (0.3, 0.7) if a.loss == "tversky" else (0.5, 0.5))
        opt.zero_grad()
        loss.backward()
        if a.opt == "sgd":
            torch.nn.utils.clip_grad_norm_(net.parameters(), 12)
        opt.step()
        sched.step()
        losses.append(loss.item())

        if step % a.val_every == 0 or step == a.steps:
            net.eval()
            scores = {p: float(dice(predict(net, img, a.patch, device, norm), lab)) for p, (img, lab) in val.items()}
            mean = float(np.mean(list(scores.values())))
            log.writerow([step, round(float(np.mean(losses)), 4), round(mean, 4), int(time.time() - t0)])
            log_file.flush()
            print(f"step {step}: loss {np.mean(losses):.3f}  val Dice {mean:.3f}  {scores}", flush=True)
            losses = []
            if mean > best:
                best, best_step, best_scores = mean, step, scores
                torch.save({"model": net.state_dict(), "args": vars(a), "norm": norm, "step": step, "val_dice": mean},
                           run / "best.pt")
    write_json(run / "summary.json", {**record, "fold": a.fold, "best_val_dice": round(best, 4), "best_step": best_step,
                                      "found": sum(d > 0.1 for d in best_scores.values()), "n_val": len(best_scores),
                                      "per_patient": {p: round(d, 4) for p, d in best_scores.items()},
                                      "minutes": round((time.time() - t0) / 60, 1),
                                      "finished": time.strftime("%Y-%m-%d %H:%M:%S")})
    print(f"best val Dice {best:.3f} -> {run / 'best.pt'}")


if __name__ == "__main__":
    main()
