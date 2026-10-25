"""Evaluate the exported ONNX model on DermNet images that were NOT used for training.

Reports accuracy, top-3 accuracy, per-class accuracy, and how accuracy/coverage change with the
confidence threshold the backend uses to decide "inconclusive". Also saves a few held-out photos
to ml/samples/ for demoing the app.

Usage: python evaluate.py --per-class 40
"""

import argparse
import io
import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pyarrow.parquet as pq
from PIL import Image

from prepare_dermnet import MAPPING, UNSUPPORTED

HERE = Path(__file__).parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, default=HERE / "output" / "skin_model.onnx")
    p.add_argument("--raw", type=Path, default=HERE / "raw")
    p.add_argument("--data", type=Path, default=HERE / "data")
    p.add_argument("--per-class", type=int, default=40)
    p.add_argument("--samples", type=int, default=3)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    meta = json.loads((args.model.parent / "labels.json").read_text())
    labels, size = meta["labels"], meta["img_size"]
    mean = np.array(meta["mean"], dtype=np.float32).reshape(3, 1, 1)
    std = np.array(meta["std"], dtype=np.float32).reshape(3, 1, 1)
    sess = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name

    used = {f.stem for f in args.data.rglob("*.jpg")}
    files = sorted(args.raw.glob("*.parquet"))
    class_names = json.loads(pq.read_schema(files[0]).metadata[b"huggingface"])["info"]["features"]["label"]["names"]

    candidates = defaultdict(list)
    for f in files:
        for i, lab in enumerate(pq.read_table(f, columns=["label"]).column("label").to_pylist()):
            name = class_names[lab]
            target = MAPPING.get(name) or ("unsupported" if name in UNSUPPORTED else None)
            if target and f"{f.stem}_{i}" not in used:
                candidates[target].append((f, i))

    rng = random.Random(args.seed)
    picks = defaultdict(list)
    for target, items in candidates.items():
        rng.shuffle(items)
        for f, i in items[: args.per_class]:
            picks[f].append((i, target))

    samples_dir = HERE / "samples"
    samples_dir.mkdir(exist_ok=True)
    saved = defaultdict(int)
    rows = []  # (true, pred, conf, top3)
    for f, items in picks.items():
        col = pq.read_table(f, columns=["image"]).column("image")
        for i, target in items:
            img = Image.open(io.BytesIO(col[i].as_py()["bytes"])).convert("RGB")
            x = np.asarray(img.resize((size, size)), dtype=np.float32) / 255.0
            x = ((x.transpose(2, 0, 1) - mean) / std)[None].astype(np.float32)
            logits = sess.run(None, {inp: x})[0][0]
            probs = np.exp(logits - logits.max())
            probs /= probs.sum()
            order = probs.argsort()[::-1]
            rows.append((target, labels[order[0]], float(probs[order[0]]), [labels[k] for k in order[:3]]))
            if saved[target] < args.samples and target != "unsupported":
                img.thumbnail((800, 800))
                img.save(samples_dir / f"{target}_{saved[target] + 1}.jpg", quality=90)
                saved[target] += 1

    n = len(rows)
    acc = sum(t == p for t, p, _, _ in rows) / n
    top3 = sum(t in t3 for t, _, _, t3 in rows) / n
    print(f"Held-out images: {n}   accuracy: {acc:.3f}   top-3 accuracy: {top3:.3f}")

    print("\nPer class:")
    by = defaultdict(list)
    for t, p, _, _ in rows:
        by[t].append(t == p)
    for t in sorted(by):
        print(f"  {t:24s} {sum(by[t]) / len(by[t]):.2f}  (n={len(by[t])})")

    # The app treats an "unsupported" prediction or low confidence as inconclusive.
    print("\nThreshold  shown-as-result  accuracy-of-shown")
    for th in (0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.7):
        shown = [(t, p) for t, p, c, _ in rows if c >= th and p != "unsupported"]
        if shown:
            print(f"  {th:.2f}       {len(shown) / n:6.1%}           {sum(t == p for t, p in shown) / len(shown):.1%}")
    print(f"\nSample photos saved to {samples_dir}")


if __name__ == "__main__":
    main()
