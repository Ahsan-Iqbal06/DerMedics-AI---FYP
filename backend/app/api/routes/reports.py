from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Analysis, Report, User
from app.schemas import ReportIn, ReportListItem, ReportOut
from app.services.pdf import render_report_pdf
from app.services.pipeline import to_out

router = APIRouter(prefix="/reports", tags=["reports"])


def _get_owned(db: Session, report_id: int, user: User) -> Report:
    report = db.get(Report, report_id)
    if report is None or report.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return report


def _report_out(db: Session, report: Report, user: User) -> ReportOut:
    return ReportOut(
        id=report.id,
        subject_type=report.subject_type,
        subject_name=report.subject_name,
        subject_age=report.subject_age,
        relationship=report.relationship_to_user,
        health_notes=report.health_notes,
        created_at=report.created_at,
        analysis=to_out(db, report.analysis, user),
    )


@router.post("", response_model=ReportOut, status_code=201)
def create_report(body: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    analysis = db.get(Analysis, body.analysis_id)
    if analysis is None or analysis.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Analysis not found")
    if analysis.report is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "A report already exists for this analysis")
    myself = body.subject_type == "myself"
    report = Report(
        user_id=user.id,
        analysis_id=analysis.id,
        subject_type=body.subject_type,
        subject_name=user.full_name if myself else body.subject_name.strip(),
        subject_age=body.subject_age,
        relationship_to_user="Self" if myself else body.relationship,
        health_notes=body.health_notes.strip(),
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return _report_out(db, report, user)


@router.get("", response_model=list[ReportListItem])
def list_reports(
    filter: Literal["all", "ai", "inconclusive"] = "all",
    q: str = Query("", max_length=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Report).join(Analysis).where(Report.user_id == user.id)
    if filter != "all":
        stmt = stmt.where(Analysis.status == filter)
    if q.strip():
        like = f"%{q.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Report.subject_name).like(like),
                func.lower(func.coalesce(Analysis.display_name, "")).like(like),
                func.lower(Analysis.body_area).like(like),
            )
        )
    stmt = stmt.order_by(Report.created_at.desc(), Report.id.desc())
    items = []
    for r in db.scalars(stmt):
        a = r.analysis
        if a.status == "ai":
            title = f"{a.display_name} • AI analysis"
            subtitle = "Report details • confidence is model-dependent"
        else:
            title = "Inconclusive result"
            subtitle = "No medicine suggestions for uncertain results"
        items.append(
            ReportListItem(
                id=r.id,
                analysis_id=a.id,
                title=title,
                subtitle=subtitle,
                status=a.status,
                subject_name=r.subject_name,
                confidence=a.confidence,
                created_at=r.created_at,
            )
        )
    return items


@router.get("/{report_id}", response_model=ReportOut)
def get_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _report_out(db, _get_owned(db, report_id, user), user)


@router.get("/{report_id}/pdf")
def report_pdf(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    report = _get_owned(db, report_id, user)
    return Response(
        render_report_pdf(report),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="dermedics-report-{report.id}.pdf"'},
    )


@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.delete(_get_owned(db, report_id, user))
    db.commit()
