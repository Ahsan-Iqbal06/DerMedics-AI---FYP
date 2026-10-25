"""Seed sample dermatologists. Run: python seed.py"""

import json

import app.models  # noqa: F401
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.models import Dermatologist


def seed() -> int:
    Base.metadata.create_all(engine)
    rows = json.loads((get_settings().data_dir / "seed_dermatologists.json").read_text(encoding="utf-8"))
    added = 0
    with SessionLocal() as db:
        existing = {(d.name, d.city) for d in db.query(Dermatologist).all()}
        for row in rows:
            if (row["name"], row["city"]) not in existing:
                db.add(Dermatologist(**row, is_sample=True))
                added += 1
        db.commit()
    return added


if __name__ == "__main__":
    print(f"Seeded {seed()} dermatologists")
