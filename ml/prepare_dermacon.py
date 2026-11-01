"""Extract DermaCon-IN images into data_parts/dermacon/{train,test}/<label>/ using the official subject-wise split.

Usage: python prepare_dermacon.py [--unsupported-cap 600]
"""

import argparse
import csv
import io
import random
import zipfile
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

from dermacon_labels import dermacon_target

HERE = Path(__file__).parent
RAW = HERE / "raw_dermacon"


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", errors="replace") as f:
        return list(csv.DictReader(f))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=HERE / "data_parts" / "dermacon")
    p.add_argument("--size", type=int, default=288)
    p.add_argument("--unsupported-cap", type=int, default=600, help="max 'other condition' images per split")
    args = p.parse_args()

    meta = {r["Image_name"]: r for r in read_csv(RAW / "Skin_Metadata.tab")}
    split_of = {}
    for split in ("train", "test"):
        for r in read_csv(RAW / f"{split}_split.tab"):
            split_of[r["Image_name"]] = split

    rng = random.Random(7)
    plan = {}  # image name -> (split, label)
    unsupported = {"train": [], "test": []}
    for name, r in meta.items():
        split = split_of.get(name)
        target = dermacon_target(r["Disease_label"], r["Quality"])
        if split is None or target is None:
            continue
        if target == "unsupported":
            unsupported[split].append(name)
        else:
            plan[name] = (split, target)
    for split, names in unsupported.items():
        rng.shuffle(names)
        for n in names[: args.unsupported_cap]:
            plan[n] = (split, "unsupported")

    counts = Counter()
    for zpath in sorted(RAW.glob("DATASET_*.zip")):
        with zipfile.ZipFile(zpath) as z:
            for member in z.namelist():
                name = member.rsplit("/", 1)[-1]
                if name not in plan:
                    continue
                split, label = plan[name]
                img = ImageOps.exif_transpose(Image.open(io.BytesIO(z.read(member)))).convert("RGB")
                scale = args.size / min(img.size)
                if scale < 1:
                    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
                out = args.out / split / label
                out.mkdir(parents=True, exist_ok=True)
                img.save(out / f"dermacon_{Path(name).stem}.jpg", quality=92)
                counts[(split, label)] += 1
        print(f"processed {zpath.name}", flush=True)
    for split in ("train", "test"):
        row = {lbl: n for (s, lbl), n in sorted(counts.items()) if s == split}
        print(split, row, "total", sum(row.values()))


if __name__ == "__main__":
    main()
