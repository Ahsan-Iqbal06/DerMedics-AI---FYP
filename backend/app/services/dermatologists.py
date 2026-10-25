import logging
import math

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import Dermatologist
from app.schemas import DermatologistOut

log = logging.getLogger(__name__)


def _distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def search_dermatologists(
    db: Session,
    *,
    country: str = "",
    city: str = "",
    q: str = "",
    condition: str | None = None,
    lat: float | None = None,
    lng: float | None = None,
    limit: int = 20,
) -> list[DermatologistOut]:
    stmt = select(Dermatologist)
    if country:
        stmt = stmt.where(func.lower(Dermatologist.country) == country.strip().lower())
    if q:
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            func.lower(Dermatologist.name).like(like)
            | func.lower(Dermatologist.clinic).like(like)
            | func.lower(Dermatologist.qualification).like(like)
            | func.lower(Dermatologist.city).like(like)
        )
    rows = list(db.scalars(stmt))

    city_l = city.strip().lower()
    results: list[DermatologistOut] = []
    for d in rows:
        out = DermatologistOut.model_validate(d)
        if lat is not None and lng is not None and d.latitude is not None and d.longitude is not None:
            out.distance_km = round(_distance_km(lat, lng, d.latitude, d.longitude), 1)
        results.append(out)

    def rank(d: DermatologistOut):
        in_city = bool(city_l) and d.city.lower() == city_l
        treats = bool(condition) and condition in d.conditions
        return (
            not in_city,
            not treats,
            d.distance_km if d.distance_km is not None else float("inf"),
            d.name,
        )

    # Same-city providers first, then those who treat the detected condition, then nearest.
    results.sort(key=rank)
    results = results[:limit]
    results.extend(_places_search(city or country, q)[: max(0, limit - len(results))])
    return results


def _places_search(area: str, q: str) -> list[DermatologistOut]:
    key = get_settings().google_places_key
    if not key or not area:
        return []
    query = f"{q or 'dermatologist'} in {area}"
    try:
        resp = httpx.post(
            "https://places.googleapis.com/v1/places:searchText",
            headers={
                "X-Goog-Api-Key": key,
                "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.location,"
                "places.rating,places.nationalPhoneNumber",
            },
            json={"textQuery": query, "maxResultCount": 10},
            timeout=10,
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        log.exception("Google Places search failed")
        return []
    out = []
    for p in resp.json().get("places", []):
        loc = p.get("location", {})
        out.append(
            DermatologistOut(
                name=p.get("displayName", {}).get("text", "Unknown"),
                kind="clinic",
                address=p.get("formattedAddress", ""),
                phone=p.get("nationalPhoneNumber", ""),
                latitude=loc.get("latitude"),
                longitude=loc.get("longitude"),
                rating=p.get("rating"),
                is_sample=False,
                source="google_places",
            )
        )
    return out
