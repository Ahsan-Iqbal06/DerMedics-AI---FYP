"""Skin-disease image classifier.

`TorchClassifier` loads a TorchScript model produced by `ml/train.py` when MODEL_PATH is set.
Until a trained model exists, `DemoClassifier` returns placeholder predictions flagged `is_demo`
so the whole app flow can be built and tested end to end.
"""

import hashlib
import io
import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageFilter, ImageStat, UnidentifiedImageError

from app.core.config import get_settings
from app.services.knowledge_base import load_conditions

log = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}
MIN_SIDE_PX = 128


class InvalidImageError(ValueError):
    pass


@dataclass
class ClassificationResult:
    predictions: list[tuple[str, float]]  # (label, probability), sorted desc
    is_demo: bool
    model_version: str
    quality_issue: str | None = None

    @property
    def top(self) -> tuple[str, float]:
        return self.predictions[0]


def load_image(data: bytes) -> Image.Image:
    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise InvalidImageError(f"Image is larger than {get_settings().max_upload_mb} MB")
    try:
        img = Image.open(io.BytesIO(data))
        img.verify()
        img = Image.open(io.BytesIO(data))
    except (UnidentifiedImageError, OSError):
        raise InvalidImageError("File is not a valid image")
    if img.format not in ALLOWED_FORMATS:
        raise InvalidImageError("Only JPG, PNG or WEBP images are supported")
    if min(img.size) < MIN_SIDE_PX:
        raise InvalidImageError(f"Image is too small; use at least {MIN_SIDE_PX}px on each side")
    return img.convert("RGB")


def quality_issue(img: Image.Image) -> str | None:
    """Cheap checks for photos that no model should be trusted on."""
    gray = img.convert("L").resize((256, 256))
    brightness = ImageStat.Stat(gray).mean[0]
    if brightness < 35:
        return "too_dark"
    if brightness > 235:
        return "overexposed"
    # Crop the frame: FIND_EDGES reports a strong edge along the image border itself.
    edges = gray.filter(ImageFilter.FIND_EDGES).crop((4, 4, 252, 252))
    sharpness = ImageStat.Stat(edges).var[0]
    if sharpness < 15:
        return "blurry"
    return None


class DemoClassifier:
    version = "demo-placeholder-v1"

    def predict(self, img: Image.Image) -> ClassificationResult:
        labels = list(load_conditions().keys())
        digest = hashlib.sha256(img.resize((64, 64)).tobytes()).digest()
        # Deterministic pseudo-scores so the same photo always gives the same demo result.
        top_idx = digest[0] % len(labels)
        top_p = 0.62 + (digest[1] / 255) * 0.3
        rest = [digest[(i + 2) % len(digest)] + 1 for i in range(len(labels))]
        rest[top_idx] = 0
        rest_total = sum(rest)
        probs = [(1 - top_p) * r / rest_total for r in rest]
        probs[top_idx] = top_p
        preds = sorted(zip(labels, probs), key=lambda p: p[1], reverse=True)
        issue = quality_issue(img)
        if issue:
            preds = [(label, p * 0.4) for label, p in preds]
        return ClassificationResult(preds, is_demo=True, model_version=self.version, quality_issue=issue)


class TorchClassifier:
    def __init__(self, model_path: Path, labels_path: Path):
        import torch  # optional dependency, see requirements-ml.txt

        self.torch = torch
        meta = json.loads(labels_path.read_text(encoding="utf-8"))
        self.labels: list[str] = meta["labels"]
        self.img_size: int = meta.get("img_size", 224)
        self.mean = meta.get("mean", [0.485, 0.456, 0.406])
        self.std = meta.get("std", [0.229, 0.224, 0.225])
        self.version = meta.get("version", model_path.stem)
        self.model = torch.jit.load(str(model_path), map_location="cpu").eval()

    def predict(self, img: Image.Image) -> ClassificationResult:
        torch = self.torch
        resized = img.resize((self.img_size, self.img_size))
        x = torch.frombuffer(bytearray(resized.tobytes()), dtype=torch.uint8)
        x = x.view(self.img_size, self.img_size, 3).permute(2, 0, 1).float() / 255.0
        x = (x - torch.tensor(self.mean).view(3, 1, 1)) / torch.tensor(self.std).view(3, 1, 1)
        with torch.no_grad():
            probs = torch.softmax(self.model(x.unsqueeze(0))[0], dim=0).tolist()
        preds = sorted(zip(self.labels, probs), key=lambda p: p[1], reverse=True)
        return ClassificationResult(preds, is_demo=False, model_version=self.version, quality_issue=quality_issue(img))


class OnnxClassifier:
    """Serves the ONNX export from ml/train.py; lighter than PyTorch for the API server."""

    def __init__(self, model_path: Path, labels_path: Path):
        import numpy as np
        import onnxruntime as ort

        self.np = np
        meta = json.loads(labels_path.read_text(encoding="utf-8"))
        self.labels: list[str] = meta["labels"]
        self.img_size: int = meta.get("img_size", 224)
        self.mean = np.array(meta.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32).reshape(3, 1, 1)
        self.std = np.array(meta.get("std", [0.229, 0.224, 0.225]), dtype=np.float32).reshape(3, 1, 1)
        self.version = meta.get("version", model_path.stem)
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        self.input_name = self.session.get_inputs()[0].name

    def predict(self, img: Image.Image) -> ClassificationResult:
        np = self.np
        x = np.asarray(img.resize((self.img_size, self.img_size)), dtype=np.float32) / 255.0
        x = (x.transpose(2, 0, 1) - self.mean) / self.std
        logits = self.session.run(None, {self.input_name: x[None].astype(np.float32)})[0][0]
        exp = np.exp(logits - logits.max())
        probs = (exp / exp.sum()).tolist()
        preds = sorted(zip(self.labels, probs), key=lambda p: p[1], reverse=True)
        return ClassificationResult(preds, is_demo=False, model_version=self.version, quality_issue=quality_issue(img))


@lru_cache
def get_classifier():
    s = get_settings()
    if s.model_path:
        model_path = Path(s.model_path)
        labels_path = Path(s.labels_path) if s.labels_path else model_path.with_name("labels.json")
        try:
            cls = OnnxClassifier if model_path.suffix == ".onnx" else TorchClassifier
            clf = cls(model_path, labels_path)
            log.info("Loaded skin classifier %s", clf.version)
            return clf
        except Exception:
            log.exception("Could not load trained model at %s; falling back to demo classifier", model_path)
    return DemoClassifier()
