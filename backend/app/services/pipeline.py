"""AI pipeline: analyze image -> describe condition -> suggest medicines -> recommend dermatologists."""

import io
import uuid

from PIL import Image
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Analysis, User
from app.schemas import AnalysisOut, ConditionInfo, MedicineSuggestion, Prediction
from app.services.classifier import get_classifier, load_image
from app.services.dermatologists import search_dermatologists
from app.services.knowledge_base import display_name
from app.services.llm import get_text_provider

# Class the model uses for conditions the app does not cover; always reported as inconclusive.
UNSUPPORTED_LABEL = "unsupported"

EXTENSIONS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def run_analysis(db: Session, user: User, image_bytes: bytes, body_area: str, symptoms: str) -> Analysis:
    s = get_settings()
    img = load_image(image_bytes)  # raises InvalidImageError

    # 1. Analyze skin image
    result = get_classifier().predict(img)
    label, confidence = result.top
    unsupported = label == UNSUPPORTED_LABEL
    confident = result.quality_issue is None and not unsupported and confidence >= s.confidence_threshold
    region = ", ".join(p for p in (user.city, user.country) if p) or "Pakistan"

    analysis = Analysis(
        user_id=user.id,
        image_path=_save_image(image_bytes),
        body_area=body_area,
        symptoms=symptoms,
        confidence=round(confidence, 4),
        top_predictions=[
            {"label": lbl, "display_name": display_name(lbl), "confidence": round(p, 4)}
            for lbl, p in result.predictions[:3]
        ],
        region=region,
        is_demo=result.is_demo,
        model_version=result.model_version,
    )

    if confident:
        # 2. Disease description, 3. Medicine suggestions (from condition + description + region)
        provider = get_text_provider()
        description = provider.describe(label, body_area, symptoms)
        medicines = provider.medicines(label, description, region)
        analysis.status = "ai"
        analysis.predicted_label = label
        analysis.display_name = description.name or display_name(label)
        analysis.description = description.model_dump()
        analysis.medicines = [m.model_dump() for m in medicines]
        analysis.llm_source = provider.source
    else:
        # Uncertain result: never show disease-specific medicine information.
        analysis.status = "inconclusive"
        analysis.medicines = []
        analysis.llm_source = result.quality_issue or ("unsupported_condition" if unsupported else "low_confidence")

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


def _save_image(data: bytes) -> str:
    s = get_settings()
    s.upload_dir.mkdir(parents=True, exist_ok=True)
    fmt = Image.open(io.BytesIO(data)).format
    name = f"{uuid.uuid4().hex}.{EXTENSIONS.get(fmt, 'jpg')}"
    (s.upload_dir / name).write_bytes(data)
    return name


def to_out(db: Session, analysis: Analysis, user: User, with_doctors: bool = True) -> AnalysisOut:
    # 4. Dermatologist recommendation (matched to region and detected condition)
    doctors = (
        search_dermatologists(
            db,
            country=user.country,
            city=user.city,
            condition=analysis.predicted_label,
            limit=5,
        )
        if with_doctors
        else []
    )
    return AnalysisOut(
        id=analysis.id,
        status=analysis.status,
        predicted_label=analysis.predicted_label,
        display_name=analysis.display_name,
        confidence=analysis.confidence,
        top_predictions=[Prediction(**p) for p in analysis.top_predictions or []],
        description=ConditionInfo(**analysis.description) if analysis.description else None,
        medicines=[MedicineSuggestion(**m) for m in analysis.medicines or []],
        region=analysis.region,
        body_area=analysis.body_area,
        symptoms=analysis.symptoms,
        is_demo=analysis.is_demo,
        model_version=analysis.model_version,
        llm_source=analysis.llm_source,
        image_url=f"/api/files/analyses/{analysis.image_path}",
        created_at=analysis.created_at,
        dermatologists=doctors,
        has_report=analysis.report is not None,
    )
