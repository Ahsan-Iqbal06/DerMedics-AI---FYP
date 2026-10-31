"""Evaluate an exported ONNX classifier on an image folder (default: data_v2/test).

Reports:
  - accuracy over the 10 app conditions (top-1, top-3)
  - "selective" accuracy: accuracy of the results the app actually shows (confidence >= threshold and not
    'unsupported'), and what share of photos get a result (coverage)
  - how many out-of-scope ('unsupported') photos are correctly withheld

Usage: python eval_onnx.py --model output/skin_model.onnx [--data data_v2/test] [--json report.json]
"""

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort
from PIL import Image

HERE = Path(__file__).parent


def preprocess(path: Path, size: int, mean, std) -> np.ndarray:
    img = Image.open(path).convert("RGB")
    # Resize shorter side then centre-crop, matching training-time evaluation.
    scale = size * 256 / 224 / min(img.size)
    img = img.resize((max(size, round(img.width * scale)), max(size, round(img.height * scale))), Image.BILINEAR)
    left, top = (img.width - size) // 2, (img.height - size) // 2
    img = img.crop((left, top, left + size, top + size))
    x = np.asarray(img, dtype=np.float32) / 255.0
    return ((x.transpose(2, 0, 1) - mean) / std).astype(np.float32)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--data", type=Path, default=HERE / "data_v2" / "test")
    p.add_argument("--thresholds", default="0.4,0.5,0.6,0.7,0.8")
    p.add_argument("--json", type=Path)
    args = p.parse_args()

    meta = json.loads((args.model.parent / "labels.json").read_text())
    labels, size = meta["labels"], meta["img_size"]
    mean = np.array(meta["mean"], dtype=np.float32).reshape(3, 1, 1)
    std = np.array(meta["std"], dtype=np.float32).reshape(3, 1, 1)
    sess = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0].name
    fixed_batch = sess.get_inputs()[0].shape[0] == 1

    rows = []  # (true, ranked labels, top prob)
    for cls_dir in sorted(d for d in args.data.iterdir() if d.is_dir()):
        files = sorted(cls_dir.glob("*.jpg"))
        for i in range(0, len(files), 32):
            batch = np.stack([preprocess(f, size, mean, std) for f in files[i : i + 32]])
            if fixed_batch:  # older exports take exactly one image
                logits = np.concatenate([sess.run(None, {inp: b[None]})[0] for b in batch])
            else:
                logits = sess.run(None, {inp: batch})[0]
            e = np.exp(logits - logits.max(1, keepdims=True))
            probs = e / e.sum(1, keepdims=True)
            for pr in probs:
                order = pr.argsort()[::-1]
                rows.append((cls_dir.name, [labels[k] for k in order[:3]], float(pr[order[0]])))

    cond = [r for r in rows if r[0] != "unsupported"]
    out = {"model": meta.get("version"), "test_images": len(rows), "condition_images": len(cond)}
    out["top1_accuracy"] = sum(r[0] == r[1][0] for r in cond) / len(cond)
    out["top3_accuracy"] = sum(r[0] in r[1] for r in cond) / len(cond)
    per = defaultdict(list)
    for t, ranked, _ in cond:
        per[t].append(t == ranked[0])
    out["per_class_recall"] = {k: round(sum(v) / len(v), 3) for k, v in sorted(per.items())}
    out["balanced_accuracy"] = float(np.mean(list(out["per_class_recall"].values())))

    unsup = [r for r in rows if r[0] == "unsupported"]
    sel = []
    for th in [float(x) for x in args.thresholds.split(",")]:
        shown = [r for r in cond if r[2] >= th and r[1][0] != "unsupported"]
        withheld_unsup = [r for r in unsup if r[2] < th or r[1][0] == "unsupported"]
        sel.append({
            "threshold": th,
            "coverage": round(len(shown) / len(cond), 3),
            "accuracy_of_shown": round(sum(r[0] == r[1][0] for r in shown) / max(len(shown), 1), 3),
            "unsupported_withheld": round(len(withheld_unsup) / max(len(unsup), 1), 3) if unsup else None,
        })
    out["selective"] = sel
    confusion = Counter((t, ranked[0]) for t, ranked, _ in cond if t != ranked[0])
    out["top_confusions"] = [f"{t} -> {p}: {n}" for (t, p), n in confusion.most_common(8)]

    print(json.dumps(out, indent=2))
    if args.json:
        args.json.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
