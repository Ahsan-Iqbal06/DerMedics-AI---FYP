"""Train a classifier head on frozen-backbone features, evaluate on the held-out test split, and export ONNX.

Steps
  1. Split DermNet-train images 85/15 into fit / validation (by image, so views of one photo never straddle).
  2. Train a linear head and an MLP head on all training views; pick by validation balanced accuracy.
  3. Choose the confidence threshold on validation (lowest threshold whose shown-results accuracy >= --target).
  4. Report on the untouched test split. With --export, write backbone + head as one ONNX model.

Usage: python train_head.py --backbone convnext_tiny [--export]
"""

import argparse
import json
import time
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).parent


def load(backbone: str, split: str):
    d = np.load(HERE / "features" / f"{backbone}_{split}.npz")
    return d["X"], d["y"], [str(s) for s in d["labels"]]


class Head(nn.Module):
    def __init__(self, dim: int, classes: int, hidden: int, mean: np.ndarray, std: np.ndarray, dropout=0.3):
        super().__init__()
        self.register_buffer("mean", torch.tensor(mean, dtype=torch.float32))
        self.register_buffer("std", torch.tensor(std, dtype=torch.float32))
        if hidden:
            self.net = nn.Sequential(nn.Dropout(dropout * 0.5), nn.Linear(dim, hidden), nn.GELU(),
                                     nn.Dropout(dropout), nn.Linear(hidden, classes))
        else:
            self.net = nn.Sequential(nn.Dropout(dropout * 0.5), nn.Linear(dim, classes))

    def forward(self, x):
        return self.net((x - self.mean) / self.std)


def train_head(Xtr, ytr, Xva, yva, classes, hidden, epochs=60, lr=1e-3, wd=1e-3, seed=0):
    torch.manual_seed(seed)
    mean, std = Xtr.mean(0), Xtr.std(0) + 1e-6
    model = Head(Xtr.shape[1], classes, hidden, mean, std)
    counts = np.bincount(ytr, minlength=classes)
    weights = torch.tensor(counts.sum() / (classes * np.maximum(counts, 1)), dtype=torch.float32)
    loss_fn = nn.CrossEntropyLoss(weight=weights, label_smoothing=0.1)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=wd)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, epochs)
    X, y = torch.tensor(Xtr), torch.tensor(ytr)
    best, best_state = -1, None
    for _ in range(epochs):
        model.train()
        perm = torch.randperm(len(X))
        for i in range(0, len(X), 256):
            idx = perm[i : i + 256]
            opt.zero_grad()
            loss_fn(model(X[idx]), y[idx]).backward()
            opt.step()
        sched.step()
        score = balanced_acc(predict(model, Xva), yva, classes)
        if score > best:
            best, best_state = score, {k: v.clone() for k, v in model.state_dict().items()}
    model.load_state_dict(best_state)
    return model, best


@torch.no_grad()
def predict(model, X_views):
    """Average class probabilities over views (test-time augmentation). X_views: (views, n, dim)."""
    model.eval()
    probs = [torch.softmax(model(torch.tensor(v)), 1).numpy() for v in X_views]
    return np.mean(probs, 0)


def balanced_acc(probs, y, classes):
    pred = probs.argmax(1)
    return float(np.mean([np.mean(pred[y == c] == c) for c in range(classes) if np.any(y == c)]))


def report(probs, y, labels, threshold):
    unsup = labels.index("unsupported") if "unsupported" in labels else -1
    cond = y != unsup
    p, yc = probs[cond], y[cond]
    pred = p.argmax(1)
    top3 = np.argsort(-p, 1)[:, :3]
    conf = p.max(1)
    shown = (conf >= threshold) & (pred != unsup)
    out = {
        "condition_images": int(cond.sum()),
        "top1_accuracy": round(float(np.mean(pred == yc)), 4),
        "top3_accuracy": round(float(np.mean([yc[i] in top3[i] for i in range(len(yc))])), 4),
        "balanced_accuracy": round(float(np.mean([np.mean(pred[yc == c] == c) for c in np.unique(yc)])), 4),
        "per_class_recall": {labels[c]: round(float(np.mean(pred[yc == c] == c)), 3) for c in np.unique(yc)},
        "threshold": round(float(threshold), 3),
        "coverage": round(float(shown.mean()), 4),
        "accuracy_of_shown": round(float(np.mean(pred[shown] == yc[shown])), 4) if shown.any() else None,
    }
    if unsup >= 0 and np.any(~cond):
        pu = probs[~cond]
        out["unsupported_withheld"] = round(float(np.mean((pu.max(1) < threshold) | (pu.argmax(1) == unsup))), 4)
    return out


def pick_threshold(probs, y, labels, target):
    unsup = labels.index("unsupported") if "unsupported" in labels else -1
    cond = y != unsup
    p, yc = probs[cond], y[cond]
    pred, conf = p.argmax(1), p.max(1)
    for th in np.arange(0.20, 0.96, 0.01):
        shown = (conf >= th) & (pred != unsup)
        if shown.sum() >= 30 and np.mean(pred[shown] == yc[shown]) >= target:
            return float(th)
    return 0.95


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backbone", required=True)
    p.add_argument("--target", type=float, default=0.80, help="accuracy wanted for results the app shows")
    p.add_argument("--export", action="store_true")
    args = p.parse_args()

    Xtr_all, ytr_all, labels = load(args.backbone, "train")  # (views, n, dim)
    Xte, yte, labels_te = load(args.backbone, "test")
    assert labels == labels_te
    classes = len(labels)
    rng = np.random.default_rng(42)
    idx = rng.permutation(Xtr_all.shape[1])
    n_val = int(0.15 * len(idx))
    va, tr = idx[:n_val], idx[n_val:]
    Xfit = Xtr_all[:, tr].reshape(-1, Xtr_all.shape[2])  # every view of every fit image
    yfit = np.tile(ytr_all[tr], Xtr_all.shape[0])
    Xva, yva = Xtr_all[:2, va], ytr_all[va]  # centre + flip views, like the test set

    results = {}
    for name, hidden in (("linear", 0), ("mlp512", 512), ("mlp1024", 1024)):
        t0 = time.time()
        model, score = train_head(Xfit, yfit, Xva, yva, classes, hidden)
        results[name] = (model, score)
        print(f"{name:8s} validation balanced acc {score:.3f}  ({time.time() - t0:.0f}s)", flush=True)
    best_name = max(results, key=lambda k: results[k][1])
    model = results[best_name][0]

    val_probs = predict(model, Xva)
    threshold = pick_threshold(val_probs, yva, labels, args.target)
    test_probs = predict(model, Xte)
    rep = {"backbone": args.backbone, "head": best_name, "validation": report(val_probs, yva, labels, threshold),
           "test": report(test_probs, yte, labels, threshold)}
    print(json.dumps(rep, indent=2))
    (HERE / "reports").mkdir(exist_ok=True)
    (HERE / "reports" / f"head_{args.backbone}.json").write_text(json.dumps(rep, indent=2))

    if args.export:
        export(args.backbone, model, labels, threshold, rep)


def export(backbone: str, head: nn.Module, labels, threshold, rep):
    from features import Backbone

    class Full(nn.Module):
        def __init__(self):
            super().__init__()
            self.backbone = Backbone(backbone)
            self.head = head

        def forward(self, x):
            return self.head(self.backbone.body(x))

    full = Full().eval()
    out = HERE / "output_v2"
    out.mkdir(exist_ok=True)
    example = torch.randn(1, 3, 224, 224)
    with torch.no_grad():
        torch.onnx.export(full, example, str(out / "skin_model.onnx"), input_names=["image"], output_names=["logits"],
                          dynamo=False, opset_version=17, dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}})
    acc = rep["test"]["top1_accuracy"]
    (out / "labels.json").write_text(json.dumps({
        "labels": labels, "img_size": 224, "mean": [0.485, 0.456, 0.406], "std": [0.229, 0.224, 0.225],
        "version": f"{backbone}-{rep['head']}-{time.strftime('%Y%m%d')}-acc{acc:.2f}",
        "test_top1": acc, "recommended_threshold": round(threshold, 2),
    }, indent=2))
    print(f"Exported {out / 'skin_model.onnx'}")


if __name__ == "__main__":
    main()
