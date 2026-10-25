"""Build ml/data/<label>/*.jpg from the DermNet parquet files in ml/raw/.

DermNet categories are mapped to the labels used by the backend (keys of backend/app/data/conditions.json).
Categories the app doesn't cover become "unsupported", which the backend reports as inconclusive.

Usage: python prepare_dermnet.py --per-class 400
"""

import argparse
import io
import json
import random
from collections import defaultdict
from pathlib import Path

import pyarrow.parquet as pq
from PIL import Image

HERE = Path(__file__).parent

MAPPING = {
    "Acne and Rosacea Photos": "acne",
    "Eczema Photos": "eczema",
    "Atopic Dermatitis Photos": "eczema",
    "Psoriasis pictures Lichen Planus and related diseases": "psoriasis",
    "Tinea Ringworm Candidiasis and other Fungal Infections": "tinea",
    "Urticaria Hives": "urticaria",
    "Warts Molluscum and other Viral Infections": "warts",
    "Scabies Lyme Disease and other Infestations and Bites": "scabies",
    "Cellulitis Impetigo and other Bacterial Infections": "impetigo",
    "Light Diseases and Disorders of Pigmentation": "pigmentation_disorder",
    "Poison Ivy Photos and other Contact Dermatitis": "contact_dermatitis",
}
UNSUPPORTED = {
    "Seborrheic Keratoses and other Benign Tumors",
    "Melanoma Skin Cancer Nevi and Moles",
    "Actinic Keratosis Basal Cell Carcinoma and other Malignant Lesions",
    "Nail Fungus and other Nail Disease",
    "Hair Loss Photos Alopecia and other Hair Diseases",
    "Vascular Tumors",
    "Bullous Disease Photos",
    "Lupus and other Connective Tissue diseases",
    "Vasculitis Photos",
    "Exanthems and Drug Eruptions",
    "Herpes HPV and other STDs Photos",
    "Systemic Disease",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", type=Path, default=HERE / "raw")
    p.add_argument("--out", type=Path, default=HERE / "data")
    p.add_argument("--per-class", type=int, default=400)
    p.add_argument("--size", type=int, default=256)
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()

    files = sorted(args.raw.glob("*.parquet"))
    # Class names live in the parquet's HF metadata; read them from the first file.
    meta = json.loads(pq.read_schema(files[0]).metadata[b"huggingface"])
    class_names = meta["info"]["features"]["label"]["names"]

    # First pass: collect (file, row) references per target label, then sample.
    refs = defaultdict(list)
    for f in files:
        labels = pq.read_table(f, columns=["label"]).column("label").to_pylist()
        for i, lab in enumerate(labels):
            name = class_names[lab]
            target = MAPPING.get(name) or ("unsupported" if name in UNSUPPORTED else None)
            if target:
                refs[target].append((f, i))

    rng = random.Random(args.seed)
    chosen = defaultdict(set)
    for target, items in refs.items():
        rng.shuffle(items)
        for f, i in items[: args.per_class]:
            chosen[f].add((i, target))

    counts = defaultdict(int)
    for f, wanted in chosen.items():
        want = dict(wanted)
        table = pq.read_table(f, columns=["image"])
        col = table.column("image")
        for i, target in want.items():
            data = col[i].as_py()["bytes"]
            try:
                img = Image.open(io.BytesIO(data)).convert("RGB")
            except Exception:
                continue
            img.thumbnail((args.size * 2, args.size * 2))
            w, h = img.size
            scale = args.size / min(w, h)
            img = img.resize((max(args.size, round(w * scale)), max(args.size, round(h * scale))))
            out = args.out / target
            out.mkdir(parents=True, exist_ok=True)
            img.save(out / f"{f.stem}_{i}.jpg", quality=90)
            counts[target] += 1
        print(f"processed {f.name}")

    for k in sorted(counts):
        print(f"{k:24s} {counts[k]}")


if __name__ == "__main__":
    main()
