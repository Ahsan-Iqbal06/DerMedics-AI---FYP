import json
from functools import lru_cache

from app.core.config import get_settings


@lru_cache
def load_conditions() -> dict[str, dict]:
    path = get_settings().data_dir / "conditions.json"
    return json.loads(path.read_text(encoding="utf-8"))


def display_name(label: str) -> str:
    if label == "unsupported":
        return "Other / unsupported condition"
    info = load_conditions().get(label)
    return info["display_name"] if info else label.replace("_", " ").title()
