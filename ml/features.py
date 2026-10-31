"""Extract image embeddings with a frozen pretrained backbone (CPU-friendly: forward passes only).

Train images get several views (centre, flip, two random crops) as cheap augmentation; test images get
centre + flip, averaged (test-time augmentation).

Usage: python features.py --backbone convnext_tiny|efficientnet_v2_s [--limit N]
Writes features/<backbone>_<split>.npz with X (views x images x dim), y, labels, paths.
"""

import argparse
import time
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torchvision import models, transforms

HERE = Path(__file__).parent
MEAN, STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]


class Backbone(torch.nn.Module):
    """Wraps a pretrained model so forward() returns one embedding per image."""

    def __init__(self, name: str):
        super().__init__()
        self.name = name
        if name == "convnext_tiny":
            m = models.convnext_tiny(weights=models.ConvNeXt_Tiny_Weights.IMAGENET1K_V1)
            self.body = torch.nn.Sequential(m.features, m.avgpool, m.classifier[0], m.classifier[1])
        elif name == "efficientnet_v2_s":
            m = models.efficientnet_v2_s(weights=models.EfficientNet_V2_S_Weights.IMAGENET1K_V1)
            self.body = torch.nn.Sequential(m.features, m.avgpool, torch.nn.Flatten())
        else:
            raise ValueError(name)
        self.eval()

    @torch.no_grad()
    def forward(self, x):
        return self.body(x)


def view_transforms(size: int, train: bool):
    norm = [transforms.ToTensor(), transforms.Normalize(MEAN, STD)]
    centre = transforms.Compose([transforms.Resize(int(size * 256 / 224)), transforms.CenterCrop(size), *norm])
    flip = transforms.Compose(
        [transforms.Resize(int(size * 256 / 224)), transforms.CenterCrop(size), transforms.RandomHorizontalFlip(1.0), *norm]
    )
    views = [centre, flip]
    if train:
        crop = transforms.Compose([
            transforms.RandomResizedCrop(size, scale=(0.5, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(0.15, 0.15, 0.1, 0.02),
            *norm,
        ])
        views += [crop, crop]
    return views


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--backbone", required=True)
    p.add_argument("--data", type=Path, default=HERE / "data_v2")
    p.add_argument("--size", type=int, default=224)
    p.add_argument("--batch", type=int, default=24)
    p.add_argument("--limit", type=int, default=0, help="images per split, for a quick timing test")
    p.add_argument("--splits", default="train,test")
    args = p.parse_args()

    torch.manual_seed(0)
    torch.set_num_threads(max(1, torch.get_num_threads()))
    model = Backbone(args.backbone)
    out_dir = HERE / "features"
    out_dir.mkdir(exist_ok=True)

    for split in args.splits.split(","):
        root = args.data / split
        labels = sorted(d.name for d in root.iterdir() if d.is_dir())
        items = [(f, labels.index(d.name)) for d in sorted(root.iterdir()) if d.is_dir() for f in sorted(d.glob("*.jpg"))]
        if args.limit:
            items = items[: args.limit]
        views = view_transforms(args.size, train=(split == "train"))
        feats = [[] for _ in views]
        t0 = time.time()
        for i in range(0, len(items), args.batch):
            imgs = [Image.open(f).convert("RGB") for f, _ in items[i : i + args.batch]]
            for v, tf in enumerate(views):
                x = torch.stack([tf(im) for im in imgs])
                feats[v].append(model(x).numpy().astype(np.float32))
            done = i + len(imgs)
            if (i // args.batch) % 20 == 0:
                rate = done / (time.time() - t0)
                print(f"{split}: {done}/{len(items)}  {rate:.1f} img/s  eta {(len(items) - done) / rate / 60:.1f} min", flush=True)
        X = np.stack([np.concatenate(f) for f in feats])
        y = np.array([c for _, c in items])
        suffix = f"_limit{args.limit}" if args.limit else ""
        np.savez_compressed(
            out_dir / f"{args.backbone}_{split}{suffix}.npz", X=X, y=y, labels=np.array(labels),
            paths=np.array([str(f.relative_to(args.data)) for f, _ in items]),
        )
        print(f"{split}: saved {X.shape} in {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
