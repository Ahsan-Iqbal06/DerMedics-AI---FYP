"""Live evaluation of the text model (descriptions + medicines) and the dermatologist recommender.

Text model, per condition:
  - structured   : reply parsed into the app's schema (description + 2-4 medicines)
  - first_line   : at least one suggested medicine is a guideline first-line option for that condition
  - precision    : share of suggested medicines that are recognised treatments for that condition
  - no_dosing    : no exact dosing schedules (the app gives general guidance only)
Reference vocabularies are drawn from standard first-line guidance (NICE CKS / AAD) and kept deliberately broad.

Recommender: for every city x condition with a matching provider, is the top result in that city and does it
treat the condition?

Usage (from backend/, uses the real .env): .venv/Scripts/python evals/eval_text_and_care.py [--json out.json]
"""

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.models import Dermatologist  # noqa: E402
from app.services.dermatologists import search_dermatologists  # noqa: E402
from app.services.knowledge_base import load_conditions  # noqa: E402
from app.services.llm import KnowledgeBaseProvider, get_text_provider  # noqa: E402

FIRST_LINE = {
    "acne": ["benzoyl", "adapalene", "tretinoin", "retinoid", "clindamycin", "azelaic", "salicylic"],
    "eczema": ["emollient", "moisturi", "hydrocortisone", "corticosteroid", "steroid", "tacrolimus", "pimecrolimus"],
    "psoriasis": ["corticosteroid", "steroid", "betamethasone", "clobetasol", "calcipotriol", "calcipotriene",
                  "vitamin d", "coal tar", "salicylic", "emollient", "moisturi"],
    "tinea": ["clotrimazole", "terbinafine", "miconazole", "ketoconazole", "econazole", "antifungal", "itraconazole"],
    "scabies": ["permethrin", "ivermectin", "benzyl benzoate", "malathion", "sulfur", "crotamiton"],
    "impetigo": ["mupirocin", "fusidic", "retapamulin", "hydrogen peroxide", "antibiotic", "flucloxacillin",
                 "cephalexin", "cefalexin"],
    "urticaria": ["cetirizine", "loratadine", "fexofenadine", "desloratadine", "levocetirizine", "antihistamine",
                  "bilastine"],
    "warts": ["salicylic", "cryotherapy", "liquid nitrogen", "duct tape", "imiquimod", "freezing"],
    "pigmentation_disorder": ["sunscreen", "spf", "azelaic", "hydroquinone", "tacrolimus", "corticosteroid",
                              "steroid", "niacinamide", "tranexamic", "phototherapy", "vitamin c", "retinoid"],
    "contact_dermatitis": ["hydrocortisone", "corticosteroid", "steroid", "emollient", "moisturi", "calamine",
                           "antihistamine", "cetirizine", "avoid"],
    "rosacea": ["metronidazole", "azelaic", "ivermectin", "brimonidine", "doxycycline", "sunscreen", "spf"],
    "melasma": ["sunscreen", "spf", "hydroquinone", "azelaic", "tranexamic", "tretinoin", "retinoid", "niacinamide"],
    "vitiligo": ["sunscreen", "spf", "corticosteroid", "steroid", "tacrolimus", "pimecrolimus", "phototherapy",
                 "ruxolitinib"],
    "seborrheic_dermatitis": ["ketoconazole", "selenium", "zinc", "ciclopirox", "hydrocortisone", "antifungal",
                              "coal tar", "salicylic"],
}
DOSING = re.compile(r"\b\d+\s?(mg|ml|g)\b.*\b(daily|twice|times|every)\b|\b\d+\s?mg\s?/\s?kg\b", re.I)


def matches(name: str, vocab: list[str]) -> bool:
    n = name.lower()
    return any(v in n for v in vocab)


def eval_text(provider) -> dict:
    rows = []
    for label in load_conditions():
        t0 = time.time()
        desc = provider.describe(label, "Arms / hands", "itchy patch for two weeks")
        meds = provider.medicines(label, desc, "Abbottabad, Pakistan")
        secs = time.time() - t0
        vocab = FIRST_LINE[label]
        text = " ".join([m.name + " " + m.usage_note for m in meds])
        rows.append({
            "condition": label,
            "seconds": round(secs, 1),
            "structured": bool(desc.overview) and 2 <= len(meds) <= 4 and len(desc.symptoms) >= 2,
            "first_line": any(matches(m.name, vocab) for m in meds),
            "precision": round(sum(matches(m.name + " " + m.usage_note, vocab) for m in meds) / max(len(meds), 1), 2),
            "no_dosing": not DOSING.search(text),
            "medicines": [m.name for m in meds],
        })
        print(f"  {label:22s} {rows[-1]['seconds']:5.1f}s  first-line={rows[-1]['first_line']}  "
              f"precision={rows[-1]['precision']}  {rows[-1]['medicines']}", flush=True)
    n = len(rows)
    return {
        "conditions": n,
        "structured_rate": sum(r["structured"] for r in rows) / n,
        "first_line_rate": sum(r["first_line"] for r in rows) / n,
        "mean_precision": round(sum(r["precision"] for r in rows) / n, 3),
        "no_dosing_rate": sum(r["no_dosing"] for r in rows) / n,
        "mean_seconds": round(sum(r["seconds"] for r in rows) / n, 1),
        "rows": rows,
    }


def eval_care() -> dict:
    with SessionLocal() as db:
        docs = db.query(Dermatologist).all()
        cases = sorted({(d.city, c) for d in docs for c in d.conditions})
        ok = 0
        for city, cond in cases:
            top = search_dermatologists(db, country="Pakistan", city=city, condition=cond, limit=3)[0]
            ok += top.city == city and cond in top.conditions
        nearest_ok = 0
        for d in docs:
            if d.latitude is None:
                continue
            top = search_dermatologists(db, country="Pakistan", lat=d.latitude, lng=d.longitude, limit=1)[0]
            nearest_ok += top.name == d.name or (top.distance_km or 99) < 0.5
        located = sum(d.latitude is not None for d in docs)
    return {"city_condition_cases": len(cases), "top1_correct": ok / len(cases),
            "nearest_by_location_correct": nearest_ok / located}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--json", type=Path)
    args = p.parse_args()
    out = {}
    provider = get_text_provider()
    print(f"Text provider: {provider.source} {getattr(provider, 'models', '')}", flush=True)
    out["llm"] = eval_text(provider)
    if provider.source != "knowledge_base":
        print("Knowledge-base fallback:", flush=True)
        out["knowledge_base"] = eval_text(KnowledgeBaseProvider())
    out["recommender"] = eval_care()
    summary = {k: {kk: vv for kk, vv in v.items() if kk != "rows"} for k, v in out.items()}
    print(json.dumps(summary, indent=2))
    if args.json:
        args.json.write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
