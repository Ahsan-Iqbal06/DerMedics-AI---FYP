"""Fine-tune a skin-disease classifier and export it for the DerMedics backend.

Dataset layout (one folder per class; folder names must match keys in backend/app/data/conditions.json):

    ml/data/
      acne/        img001.jpg ...
      eczema/      ...
      psoriasis/   ...

Usage:
    python train.py --data data --epochs 15 --arch efficientnet_b0
Outputs (in --out, default ml/output):
    skin_model.onnx ONNX model (served by backend OnnxClassifier; needs only onnxruntime)
    skin_model.pt   TorchScript model (alternative, served by TorchClassifier)
    labels.json     class labels + preprocessing metadata

Then copy skin_model.onnx and labels.json to backend/models_store/ and set
MODEL_PATH=models_store/skin_model.onnx in backend/.env.
"""

import argparse
import json
import random
import time
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, Subset
from torchvision import datasets, models, transforms

MEAN = [0.485, 0.456, 0.406]
STD = [0.229, 0.224, 0.225]


def build_model(arch: str, num_classes: int) -> nn.Module:
    if arch == "efficientnet_b0":
        m = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.DEFAULT)
        m.classifier[1] = nn.Linear(m.classifier[1].in_features, num_classes)
    elif arch == "mobilenet_v3_large":
        # Fastest option for CPU-only training.
        m = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.DEFAULT)
        m.classifier[3] = nn.Linear(m.classifier[3].in_features, num_classes)
    elif arch == "resnet50":
        m = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        m.fc = nn.Linear(m.fc.in_features, num_classes)
    else:
        raise ValueError(f"Unknown arch {arch}")
    return m


def split_indices(n: int, val_ratio: float, seed: int) -> tuple[list[int], list[int]]:
    idx = list(range(n))
    random.Random(seed).shuffle(idx)
    cut = int(n * (1 - val_ratio))
    return idx[:cut], idx[cut:]


def evaluate(model, loader, device) -> tuple[float, float]:
    model.eval()
    correct = total = 0
    loss_sum = 0.0
    criterion = nn.CrossEntropyLoss()
    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            out = model(x)
            loss_sum += criterion(out, y).item() * y.size(0)
            correct += (out.argmax(1) == y).sum().item()
            total += y.size(0)
    return loss_sum / max(total, 1), correct / max(total, 1)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path(__file__).parent / "data")
    p.add_argument("--out", type=Path, default=Path(__file__).parent / "output")
    p.add_argument("--arch", default="efficientnet_b0", choices=["efficientnet_b0", "mobilenet_v3_large", "resnet50"])
    p.add_argument("--epochs", type=int, default=15)
    p.add_argument("--batch-size", type=int, default=32)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--img-size", type=int, default=224)
    p.add_argument("--val-ratio", type=float, default=0.15)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--workers", type=int, default=0, help="DataLoader worker processes (0 is safest on Windows)")
    p.add_argument("--resume", action="store_true", help="Continue from output/checkpoint.pt")
    args = p.parse_args()

    torch.manual_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "mps" if torch.backends.mps.is_available() else "cpu"
    print(f"Device: {device}")

    train_tf = transforms.Compose([
        transforms.RandomResizedCrop(args.img_size, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ColorJitter(0.2, 0.2, 0.1, 0.02),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])
    val_tf = transforms.Compose([
        transforms.Resize((args.img_size, args.img_size)),
        transforms.ToTensor(),
        transforms.Normalize(MEAN, STD),
    ])

    base = datasets.ImageFolder(args.data)
    labels = base.classes
    print(f"Classes ({len(labels)}): {labels}  •  images: {len(base)}")
    tr_idx, va_idx = split_indices(len(base), args.val_ratio, args.seed)
    train_ds = Subset(datasets.ImageFolder(args.data, transform=train_tf), tr_idx)
    val_ds = Subset(datasets.ImageFolder(args.data, transform=val_tf), va_idx)
    train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True, num_workers=args.workers)
    val_dl = DataLoader(val_ds, batch_size=args.batch_size, num_workers=args.workers)

    # Class weights counter dataset imbalance (common in dermatology datasets).
    counts = torch.bincount(torch.tensor([base.targets[i] for i in tr_idx]), minlength=len(labels)).float()
    weights = (counts.sum() / (len(labels) * counts.clamp(min=1))).to(device)

    model = build_model(args.arch, len(labels)).to(device)
    criterion = nn.CrossEntropyLoss(weight=weights, label_smoothing=0.1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    args.out.mkdir(parents=True, exist_ok=True)
    ckpt_path = args.out / "checkpoint.pt"
    start_epoch, best_acc = 1, 0.0
    if args.resume and ckpt_path.exists():
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model"])
        optimizer.load_state_dict(ckpt["optimizer"])
        scheduler.load_state_dict(ckpt["scheduler"])
        start_epoch, best_acc = ckpt["epoch"] + 1, ckpt["best_acc"]
        print(f"Resumed from epoch {ckpt['epoch']} (best val_acc {best_acc:.3f})")

    for epoch in range(start_epoch, args.epochs + 1):
        model.train()
        t0 = time.time()
        for x, y in train_dl:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(x), y)
            loss.backward()
            optimizer.step()
        scheduler.step()
        val_loss, val_acc = evaluate(model, val_dl, device)
        print(f"epoch {epoch:02d}  val_loss {val_loss:.4f}  val_acc {val_acc:.3f}  ({time.time() - t0:.0f}s)")
        if val_acc > best_acc:
            best_acc = val_acc
            # Export as soon as the model improves, so a crash later never loses the best result.
            export(model, args, labels, best_acc)
        # Checkpoint every epoch so an interrupted run can continue with --resume.
        torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "scheduler": scheduler.state_dict(), "epoch": epoch, "best_acc": best_acc}, ckpt_path)
    print(f"Done. Best val_acc {best_acc:.3f}")


def export(model: nn.Module, args, labels: list[str], best_acc: float) -> None:
    was_training = model.training
    model.eval()
    example = torch.randn(1, 3, args.img_size, args.img_size)
    with torch.no_grad():
        torch.jit.trace(model, example).save(str(args.out / "skin_model.pt"))
        torch.onnx.export(model, example, str(args.out / "skin_model.onnx"), input_names=["image"],
                          output_names=["logits"], dynamo=False, opset_version=17,
                          dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}})
    version = f"{args.arch}-{time.strftime('%Y%m%d')}-acc{best_acc:.2f}"
    (args.out / "labels.json").write_text(json.dumps({
        "labels": labels,
        "img_size": args.img_size,
        "mean": MEAN,
        "std": STD,
        "version": version,
        "val_accuracy": best_acc,
    }, indent=2))
    print(f"Saved {args.out / 'skin_model.onnx'}  ({version})")
    model.train(was_training)


if __name__ == "__main__":
    main()
