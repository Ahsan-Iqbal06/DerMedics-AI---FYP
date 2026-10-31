"""Build a clean dataset from DermNet with the official train/test split kept separate.

  data_v2/train/<label>/*.jpg   from DermNet's train split only (used for training + validation)
  data_v2/test/<label>/*.jpg    from DermNet's test split only (used once, for the final report)

Labels are the app's 10 conditions plus "unsupported" (a capped sample of the other DermNet categories),
so the test can also measure how often out-of-scope photos are correctly rejected.

Usage: python prepare_v2.py [--unsupported-train 1200] [--unsupported-test 400]
"""

import argparse
import io
import json
import random
from collections import Counter
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

from prepare_dermnet import MAPPING, UNSUPPORTED

HERE = Path(__file__).parent


def target_of(name: str) -> str | None:
    return MAPPING.get(name) or ("unsupported" if name in UNSUPPORTED else None)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, default=HERE / "raw")
    p.add_argument("--out", type=Path, default=HERE / "data_v2")
    p.add_argument("--size", type=int, default=288, help="shorter side after resize")
    p.add_argument("--unsupported-train", type=int, default=1200)
    p.add_argument("--unsupported-test", type=int, default=400)
    p.add_argument("--seed", type=int, default=13)
    args = p.parse_args()

    files = sorted(args.raw.glob("*.parquet"))
    names = json.loads(pq.read_schema(files[0]).metadata[b"huggingface"])["info"]["features"]["label"]["names"]
    rng = random.Random(args.seed)
    caps = {"train": args.unsupported_train, "test": args.unsupported_test}

    for split in ("train", "test"):
        split_files = [f for f in files if f.name.startswith(split)]
        # Decide which unsupported rows to keep (random sample, capped) before decoding any images.
        unsupported_rows = []
        for f in split_files:
            labels = pq.read_table(f, columns=["label"]).column("label").to_pylist()
            unsupported_rows += [(f.name, i) for i, lab in enumerate(labels) if target_of(names[lab]) == "unsupported"]
        rng.shuffle(unsupported_rows)
        keep_unsupported = set(unsupported_rows[: caps[split]])

        counts = Counter()
        for f in split_files:
            t = pq.read_table(f, columns=["image", "label"])
            labels = t.column("label").to_pylist()
            images = t.column("image")
            for i, lab in enumerate(labels):
                target = target_of(names[lab])
                if target is None or (target == "unsupported" and (f.name, i) not in keep_unsupported):
                    continue
                img = Image.open(io.BytesIO(images[i].as_py()["bytes"])).convert("RGB")
                scale = args.size / min(img.size)
                if scale < 1:
                    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
                out = args.out / split / target
                out.mkdir(parents=True, exist_ok=True)
                img.save(out / f"{f.stem}_{i}.jpg", quality=92)
                counts[target] += 1
            del t
            print(f"{split}: processed {f.name}", flush=True)
        print(split, dict(sorted(counts.items())), "total", sum(counts.values()), flush=True)


if __name__ == "__main__":
    main()
