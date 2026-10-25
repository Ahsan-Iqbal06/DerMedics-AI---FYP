from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Analysis, Dermatologist, Report, User
from app.schemas import ActivityItem, DashboardOut, DermatologistOut
from app.services.dermatologists import search_dermatologists

router = APIRouter(tags=["care"])


@router.get("/dermatologists", response_model=list[DermatologistOut])
def dermatologists(
    country: str = Query("", max_length=80),
    city: str = Query("", max_length=80),
    q: str = Query("", max_length=100),
    condition: str | None = Query(None, max_length=80),
    lat: float | None = Query(None, ge=-90, le=90),
    lng: float | None = Query(None, ge=-180, le=180),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return search_dermatologists(
        db,
        country=country or user.country,
        city=city if city or lat is not None else user.city,
        q=q,
        condition=condition,
        lat=lat,
        lng=lng,
    )


@router.get("/dashboard", response_model=DashboardOut)
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analyses = db.scalar(select(func.count()).select_from(Analysis).where(Analysis.user_id == user.id)) or 0
    reports = db.scalar(select(func.count()).select_from(Report).where(Report.user_id == user.id)) or 0
    nearby = db.scalar(
        select(func.count())
        .select_from(Dermatologist)
        .where(func.lower(Dermatologist.city) == user.city.lower())
    ) or 0

    activity: list[ActivityItem] = []
    for a in db.scalars(select(Analysis).where(Analysis.user_id == user.id).order_by(Analysis.id.desc()).limit(5)):
        title = f"Skin analysis • {a.display_name}" if a.status == "ai" else "Skin analysis • Inconclusive"
        activity.append(ActivityItem(kind="analysis", title=title, ref_id=a.id, created_at=a.created_at))
    for r in db.scalars(select(Report).where(Report.user_id == user.id).order_by(Report.id.desc()).limit(5)):
        activity.append(ActivityItem(kind="report", title="PDF report ready", ref_id=r.id, created_at=r.created_at))
    activity.sort(key=lambda i: (i.created_at is not None, i.created_at, i.ref_id), reverse=True)

    return DashboardOut(
        analyses_count=analyses, reports_count=reports, nearby_count=nearby, recent_activity=activity[:5]
    )
